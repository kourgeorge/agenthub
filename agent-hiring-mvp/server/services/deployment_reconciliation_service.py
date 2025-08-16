"""Deployment reconciliation service for maintaining consistency between database and Docker runtime."""

import logging
import docker
from docker import errors as docker_errors
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from ..models.deployment import AgentDeployment, DeploymentStatus
from ..models.hiring import Hiring, HiringStatus

logger = logging.getLogger(__name__)


class DeploymentReconciliationService:
    """Service for reconciling deployment states with actual Docker containers."""
    
    def __init__(self, db: Session):
        self.db = db
        self.docker_client = docker.from_env()
    
    def reconcile_all_deployments(self) -> Dict[str, Any]:
        """Reconcile all deployments to ensure database state matches Docker runtime."""
        try:
            logger.info("Starting deployment reconciliation...")
            
            # Get all deployments that should have containers (including stopped/suspended ones)
            active_deployments = self.db.query(AgentDeployment).filter(
                AgentDeployment.status.in_([
                    DeploymentStatus.RUNNING.value,
                    DeploymentStatus.BUILDING.value,
                    DeploymentStatus.DEPLOYING.value,
                    DeploymentStatus.STOPPED.value  # Include stopped deployments to validate container state
                ])
            ).all()
            
            reconciliation_results = {
                "total_deployments": len(active_deployments),
                "reconciled": 0,
                "status_changes": [],
                "orphaned_containers": 0,
                "errors": []
            }
            
            for deployment in active_deployments:
                try:
                    result = self._reconcile_single_deployment(deployment)
                    if result["status_changed"]:
                        reconciliation_results["status_changes"].append(result)
                        reconciliation_results["reconciled"] += 1
                except Exception as e:
                    error_msg = f"Error reconciling deployment {deployment.deployment_id}: {str(e)}"
                    logger.error(error_msg)
                    reconciliation_results["errors"].append(error_msg)
            
            # Identify containers without database records (READ-ONLY - no cleanup)
            orphaned_containers = self._identify_orphaned_containers()
            reconciliation_results["orphaned_containers_found"] = len(orphaned_containers)
            reconciliation_results["orphaned_containers_details"] = orphaned_containers
            
            logger.info(f"Deployment reconciliation completed: {reconciliation_results['reconciled']} deployments reconciled, {len(orphaned_containers)} orphaned containers identified (NOT removed)")
            
            return reconciliation_results
            
        except Exception as e:
            error_msg = f"Failed to reconcile deployments: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg}
    
    def _reconcile_single_deployment(self, deployment: AgentDeployment) -> Dict[str, Any]:
        """Reconcile a single deployment's state with Docker runtime."""
        result = {
            "deployment_id": deployment.deployment_id,
            "old_status": deployment.status,
            "new_status": deployment.status,
            "status_changed": False,
            "reason": None
        }
        
        try:
            # Check if container exists and is accessible
            if not deployment.container_name:
                # Deployment has no container name - this is the issue we're fixing
                result["new_status"] = DeploymentStatus.FAILED.value
                result["status_changed"] = True
                result["reason"] = "No container name - deployment incomplete"
                
                # Update deployment status
                deployment.status = DeploymentStatus.FAILED.value
                deployment.status_message = "Deployment incomplete - missing container name"
                deployment.stopped_at = datetime.now(timezone.utc)
                deployment.is_healthy = False
                
                logger.warning(f"Deployment {deployment.deployment_id} marked as failed due to missing container name")
                
            else:
                # Check if container exists in Docker
                try:
                    container = self.docker_client.containers.get(deployment.container_name)
                    container_status = container.status
                    
                    # Map Docker container status to deployment status
                    if container_status == "running":
                        if deployment.status != DeploymentStatus.RUNNING.value:
                            result["new_status"] = DeploymentStatus.RUNNING.value
                            result["status_changed"] = True
                            result["reason"] = f"Container is running (Docker status: {container_status})"
                            
                            deployment.status = DeploymentStatus.RUNNING.value
                            deployment.started_at = datetime.now(timezone.utc)
                            deployment.is_healthy = True
                            deployment.health_check_failures = 0
                    
                    elif container_status == "exited":
                        if deployment.status == DeploymentStatus.RUNNING.value:
                            result["new_status"] = DeploymentStatus.CRASHED.value
                            result["status_changed"] = True
                            result["reason"] = f"Container exited (Docker status: {container_status})"
                            
                            deployment.status = DeploymentStatus.CRASHED.value
                            deployment.stopped_at = datetime.now(timezone.utc)
                            deployment.is_healthy = False
                            deployment.status_message = f"Container exited with status: {container.attrs.get('State', {}).get('ExitCode', 'unknown')}"
                    
                    elif container_status == "stopped":
                        if deployment.status == DeploymentStatus.RUNNING.value:
                            result["new_status"] = DeploymentStatus.STOPPED.value
                            result["status_changed"] = True
                            result["reason"] = f"Container stopped (Docker status: {container_status})"
                            
                            deployment.status = DeploymentStatus.STOPPED.value
                            deployment.stopped_at = datetime.now(timezone.utc)
                            deployment.is_healthy = False
                        elif deployment.status == DeploymentStatus.STOPPED.value:
                            # Container is stopped and deployment is marked as stopped - this is correct for suspended hirings
                            result["reason"] = f"Container correctly stopped (Docker status: {container_status}) - deployment status matches"
                            # No status change needed - this is the expected state for suspended hirings
                    
                    elif container_status == "created":
                        if deployment.status == DeploymentStatus.RUNNING.value:
                            result["new_status"] = DeploymentStatus.DEPLOYING.value
                            result["status_changed"] = True
                            result["reason"] = f"Container created but not started (Docker status: {container_status})"
                            
                            deployment.status = DeploymentStatus.DEPLOYING.value
                            deployment.is_healthy = False
                    
                    else:
                        # Unknown container status
                        if deployment.status == DeploymentStatus.RUNNING.value:
                            result["new_status"] = DeploymentStatus.FAILED.value
                            result["status_changed"] = True
                            result["reason"] = f"Unknown container status: {container_status}"
                            
                            deployment.status = DeploymentStatus.FAILED.value
                            deployment.status_message = f"Unknown container status: {container_status}"
                            deployment.stopped_at = datetime.now(timezone.utc)
                            deployment.is_healthy = False
                
                except docker_errors.NotFound:
                    # Container doesn't exist in Docker
                    if deployment.status in [DeploymentStatus.RUNNING.value, DeploymentStatus.BUILDING.value, DeploymentStatus.DEPLOYING.value]:
                        result["new_status"] = DeploymentStatus.FAILED.value
                        result["status_changed"] = True
                        result["reason"] = "Container not found in Docker"
                        
                        deployment.status = DeploymentStatus.FAILED.value
                        deployment.status_message = "Container not found in Docker runtime"
                        deployment.stopped_at = datetime.now(timezone.utc)
                        deployment.is_healthy = False
                        deployment.container_id = None
                        deployment.container_name = None
                        
                        logger.warning(f"Deployment {deployment.deployment_id} marked as failed - container not found in Docker")
                    
                    elif deployment.status == DeploymentStatus.CANCELLED.value:
                        # Cancelled deployments are legitimate and should not have containers
                        result["reason"] = "Deployment is cancelled - no container expected"
                        # No status change needed - this is the correct state
                    
                    elif deployment.status == DeploymentStatus.STOPPED.value:
                        # Stopped deployments might not have containers (e.g., if they were cleaned up)
                        result["reason"] = "Deployment is stopped - container may have been cleaned up"
                        # No status change needed - this could be legitimate
                
                except Exception as e:
                    # Docker API error
                    logger.error(f"Error checking container {deployment.container_name} for deployment {deployment.deployment_id}: {str(e)}")
                    result["reason"] = f"Docker API error: {str(e)}"
            
            # Update database if status changed
            if result["status_changed"]:
                self.db.commit()
                logger.info(f"Deployment {deployment.deployment_id} status updated: {result['old_status']} -> {result['new_status']} ({result['reason']})")
            
            return result
            
        except Exception as e:
            logger.error(f"Error reconciling deployment {deployment.deployment_id}: {str(e)}")
            result["reason"] = f"Reconciliation error: {str(e)}"
            return result
    
    def _identify_orphaned_containers(self) -> List[Dict[str, Any]]:
        """Identify AgentHub Docker containers that don't have corresponding database records (READ-ONLY)."""
        try:
            # Get all containers (running and stopped)
            all_containers = self.docker_client.containers.list(all=True)
            # Filter for only AgentHub containers (starting with 'aghub-')
            containers = [c for c in all_containers if c.name.startswith('aghub-')]
            orphaned_containers = []
            
            for container in containers:
                try:
                    # Check if container name matches any deployment
                    container_name = container.name
                    deployment = self.db.query(AgentDeployment).filter(
                        AgentDeployment.container_name == container_name
                    ).first()
                    
                    if not deployment:
                        # This AgentHub container has no database record - log it but don't remove
                        container_info = {
                            "name": container_name,
                            "id": container.id[:12],  # Short ID
                            "status": container.status,
                            "image": container.image.tags[0] if container.image.tags else container.image.id[:12],
                            "created": container.attrs.get('Created', 'Unknown'),
                            "warning": "No AgentHub deployment record found - this is an anomaly"
                        }
                        orphaned_containers.append(container_info)
                        
                        logger.info(f"Found AgentHub container without deployment record: {container_name} (ID: {container.id[:12]}) - NOT removing (orphaned AgentHub container)")
                        
                except Exception as e:
                    logger.error(f"Error checking container {container.name}: {str(e)}")
                    continue
            
            return orphaned_containers
            
        except Exception as e:
            logger.error(f"Error identifying orphaned containers: {str(e)}")
            return []
    
    def reconcile_deployment_by_id(self, deployment_id: str) -> Dict[str, Any]:
        """Reconcile a specific deployment by ID."""
        try:
            deployment = self.db.query(AgentDeployment).filter(
                AgentDeployment.deployment_id == deployment_id
            ).first()
            
            if not deployment:
                return {"error": "Deployment not found"}
            
            result = self._reconcile_single_deployment(deployment)
            return result
            
        except Exception as e:
            error_msg = f"Failed to reconcile deployment {deployment_id}: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg}
    
    def get_deployment_health_summary(self) -> Dict[str, Any]:
        """Get a summary of deployment health status."""
        try:
            # ============================================================================
            # DATABASE HIRINGS STATISTICS
            # ============================================================================
            total_hirings = self.db.query(Hiring).count()
            active_hirings = self.db.query(Hiring).filter(Hiring.status == "active").count()
            suspended_hirings = self.db.query(Hiring).filter(Hiring.status == "suspended").count()
            cancelled_hirings = self.db.query(Hiring).filter(Hiring.status == "cancelled").count()
            expired_hirings = self.db.query(Hiring).filter(Hiring.status == "expired").count()
            
            # ============================================================================
            # DATABASE DEPLOYMENTS STATISTICS
            # ============================================================================
            total_deployments = self.db.query(AgentDeployment).count()
            running_deployments = self.db.query(AgentDeployment).filter(
                AgentDeployment.status == DeploymentStatus.RUNNING.value
            ).count()
            stopped_deployments = self.db.query(AgentDeployment).filter(
                AgentDeployment.status == DeploymentStatus.STOPPED.value
            ).count()
            failed_deployments = self.db.query(AgentDeployment).filter(
                AgentDeployment.status == DeploymentStatus.FAILED.value
            ).count()
            cancelled_deployments = self.db.query(AgentDeployment).filter(
                AgentDeployment.status == DeploymentStatus.CANCELLED.value
            ).count()
            building_deployments = self.db.query(AgentDeployment).filter(
                AgentDeployment.status == DeploymentStatus.BUILDING.value
            ).count()
            deploying_deployments = self.db.query(AgentDeployment).filter(
                AgentDeployment.status == DeploymentStatus.DEPLOYING.value
            ).count()
            
            # ============================================================================
            # DOCKER CONTAINERS STATISTICS (AGENTHUB ONLY)
            # ============================================================================
            try:
                all_containers = self.docker_client.containers.list(all=True)
                # Filter for only AgentHub containers (starting with 'aghub-')
                containers = [c for c in all_containers if c.name.startswith('aghub-')]
                total_containers = len(containers)
                running_containers = len([c for c in containers if c.status == "running"])
                stopped_containers = len([c for c in containers if c.status == "stopped"])
                exited_containers = len([c for c in containers if c.status == "exited"])
                created_containers = len([c for c in containers if c.status == "created"])
            except Exception as e:
                logger.error(f"Error getting Docker container stats: {e}")
                total_containers = 0
                running_containers = 0
                stopped_containers = 0
                exited_containers = 0
                created_containers = 0
            
            # ============================================================================
            # ANOMALIES DETECTION (MISMATCHES BETWEEN DB AND DOCKER)
            # ============================================================================
            # Running deployments without containers
            running_without_containers = self.db.query(AgentDeployment).filter(
                AgentDeployment.status == DeploymentStatus.RUNNING.value,
                AgentDeployment.container_name.is_(None)
            ).count()
            
            # Stopped deployments that should be running (active hirings)
            stopped_should_be_running = self.db.query(AgentDeployment).join(Hiring).filter(
                AgentDeployment.status == DeploymentStatus.STOPPED.value,
                Hiring.status == "active",
                AgentDeployment.container_name.isnot(None)
            ).count()
            
            # Failed deployments that should be running (active hirings)
            failed_should_be_running = self.db.query(AgentDeployment).join(Hiring).filter(
                AgentDeployment.status == DeploymentStatus.FAILED.value,
                Hiring.status == "active"
            ).count()
            
            # Containers without database records (orphaned)
            orphaned_containers = len(self._identify_orphaned_containers())
            
            # Total anomalies
            total_anomalies = running_without_containers + stopped_should_be_running + failed_should_be_running + orphaned_containers
            
            return {
                # Database Hirings
                "total_hirings": total_hirings,
                "active_hirings": active_hirings,
                "suspended_hirings": suspended_hirings,
                "cancelled_hirings": cancelled_hirings,
                "expired_hirings": expired_hirings,
                
                # Database Deployments
                "total_deployments": total_deployments,
                "running_deployments": running_deployments,
                "stopped_deployments": stopped_deployments,
                "failed_deployments": failed_deployments,
                "cancelled_deployments": cancelled_deployments,
                "building_deployments": building_deployments,
                "deploying_deployments": deploying_deployments,
                
                # Docker Containers
                "total_containers": total_containers,
                "running_containers": running_containers,
                "stopped_containers": stopped_containers,
                "exited_containers": exited_containers,
                "created_containers": created_containers,
                
                # Anomalies
                "total_anomalies": total_anomalies,
                "running_without_containers": running_without_containers,
                "stopped_should_be_running": stopped_should_be_running,
                "failed_should_be_running": failed_should_be_running,
                "orphaned_containers": orphaned_containers,
                
                "note": "Reconciliation is READ-ONLY - Only AgentHub containers (aghub-*) are considered"
            }
            
        except Exception as e:
            logger.error(f"Error getting deployment health summary: {str(e)}")
            return {"error": str(e)}
    
    def validate_hiring_deployment_consistency(self) -> Dict[str, Any]:
        """Validate consistency between hiring status and deployment status."""
        try:
            # Get all hirings with their deployments
            hirings_with_deployments = self.db.query(Hiring).join(AgentDeployment).all()
            
            inconsistencies = []
            valid_pairs = []
            
            for hiring in hirings_with_deployments:
                deployment = hiring.deployments[0] if hiring.deployments else None
                
                if not deployment:
                    continue
                
                # Check for inconsistencies
                if hiring.status == "suspended" and deployment.status != DeploymentStatus.STOPPED.value:
                    inconsistencies.append({
                        "hiring_id": hiring.id,
                        "deployment_id": deployment.deployment_id,
                        "hiring_status": hiring.status,
                        "deployment_status": deployment.status,
                        "expected_deployment_status": DeploymentStatus.STOPPED.value,
                        "issue": "Suspended hiring should have stopped deployment"
                    })
                elif hiring.status == "active" and deployment.status == DeploymentStatus.STOPPED.value:
                    inconsistencies.append({
                        "hiring_id": hiring.id,
                        "deployment_id": deployment.deployment_id,
                        "hiring_status": hiring.status,
                        "deployment_status": deployment.status,
                        "expected_deployment_status": DeploymentStatus.RUNNING.value,
                        "issue": "Active hiring should have running deployment"
                    })
                elif hiring.status == "cancelled" and deployment.status != DeploymentStatus.CANCELLED.value:
                    inconsistencies.append({
                        "hiring_id": hiring.id,
                        "deployment_id": deployment.deployment_id,
                        "hiring_status": hiring.status,
                        "deployment_status": deployment.status,
                        "expected_deployment_status": DeploymentStatus.CANCELLED.value,
                        "issue": "Cancelled hiring should have cancelled deployment"
                    })
                else:
                    valid_pairs.append({
                        "hiring_id": hiring.id,
                        "deployment_id": deployment.deployment_id,
                        "hiring_status": hiring.status,
                        "deployment_status": deployment.status
                    })
            
            return {
                "total_hirings_checked": len(hirings_with_deployments),
                "valid_pairs": len(valid_pairs),
                "inconsistencies": len(inconsistencies),
                "inconsistency_details": inconsistencies,
                "valid_pairs_details": valid_pairs
            }
            
        except Exception as e:
            logger.error(f"Error validating hiring-deployment consistency: {str(e)}")
            return {"error": str(e)}
