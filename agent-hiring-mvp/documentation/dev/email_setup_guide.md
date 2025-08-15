# Email Service Setup Guide

## Gmail SMTP Configuration

The AgentHub application uses Gmail SMTP to send emails for:
- Password reset requests
- New password delivery
- Email verification
- Welcome emails

## Setup Steps

### 1. Enable 2-Step Verification
1. Go to your [Google Account settings](https://myaccount.google.com/)
2. Navigate to Security
3. Enable 2-Step Verification if not already enabled

### 2. Generate App Password
1. In Security settings, find "App passwords"
2. Click "App passwords"
3. Select "Mail" as the app
4. Select "Other" as the device
5. Enter "AgentHub" as the name
6. Click "Generate"
7. Copy the 16-character password (e.g., `abcd efgh ijkl mnop`)

### 3. Create .env File
Create a `.env` file in the `agent-hiring-mvp` directory with the following content:

```bash
# Email Configuration
GMAIL_SMTP_SERVER=smtp.gmail.com
GMAIL_SMTP_PORT=587
GMAIL_EMAIL=kourgeorge@gmail.com
GMAIL_APP_PASSWORD=your_16_character_app_password

# Company Settings
COMPANY_NAME=AgentHub
SUPPORT_EMAIL=support@agenthub.com
```

**Important**: Replace `your_16_character_app_password` with the actual App Password you generated.

### 4. Test the Configuration
Run the test script to verify everything works:

```bash
cd agent-hiring-mvp
python test_email.py
```

## Security Notes

- **Never use your regular Gmail password** - it won't work and is less secure
- **App Passwords are 16 characters** with spaces (remove spaces when copying)
- **App Passwords can be revoked** if you suspect they're compromised
- **2-Step Verification is required** to generate App Passwords

## Troubleshooting

### Common Issues

1. **Authentication Failed**
   - Make sure you're using an App Password, not your regular password
   - Verify 2-Step Verification is enabled
   - Check that the App Password was copied correctly

2. **Connection Refused**
   - Verify SMTP server: `smtp.gmail.com`
   - Verify SMTP port: `587`
   - Check your firewall/network settings

3. **Email Not Received**
   - Check spam/junk folder
   - Verify the recipient email address
   - Check Gmail's "Sent" folder to confirm delivery

### Alternative Email Services

If Gmail doesn't work for you, you can modify the email service to use:
- **SendGrid** (recommended for production)
- **AWS SES**
- **Mailgun**
- **SMTP from your own domain**

## Production Considerations

For production use, consider:
1. **Environment Variables**: Store credentials in environment variables, not in code
2. **Email Templates**: Use professional HTML templates
3. **Rate Limiting**: Implement email rate limiting to prevent abuse
4. **Monitoring**: Add logging and monitoring for email delivery
5. **Fallback**: Have backup email service providers

## Support

If you encounter issues:
1. Check the test script output for specific error messages
2. Verify your Gmail account settings
3. Test with a simple email client first
4. Check the application logs for detailed error information
