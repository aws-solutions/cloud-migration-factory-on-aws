#!/usr/bin/env python
import sys
if not sys.warnoptions:
    import warnings
    warnings.simplefilter("ignore")

def lambda_handler(event, context):
    """
    Send Email Lambda handler. 
    The Task Orchestrator lambda pushes events to event bus when script name is 'Send Email',
    which then triggers the Email Notification Lambda. This lambda handler simply logs this action.
    """
    try:
        # Log the email sending action
        print(f"Sending email...")

        return {
            "status": "success",
            "message": "Email sending action logged"
        }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }
