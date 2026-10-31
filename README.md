POST-FLOOD WASTE MANAGEMENT SYSTEM DETAILS:


SETUPS:

Requirements:
    Python 3.10+
    PyQt6

Test Administrator:
    Username: admin
    Password: admin123


SYSTEM PROGRESS:

Progress 1: Core System Setup, Login and Registration System, and Role-Based Dashboards - ASAJAR

- Created the basic system structure using PyQt6.
- Added login and registration features.
- Added password security and input validation.
- Created separate admin and volunteer dashboard windows as 
    the initial interfaces for future features.
- Added login and logout functionality.
- Applied a consistent user interface design.
- Prepared the system for future waste management features.


Progress 2: Dashboard Development, Volunteer and Admin Features - MAPAS, RAMOS, URBANO

- Developed the main admin and volunteer dashboards with 
    navigation bars and corresponding actions.
- Redesigned the user interface and updated style.qss for 
    a more consistent and organized appearance.
- Added admin functions for creating cleanup tasks and 
    sending announcements or notifications to volunteers.
- Added volunteer functions for viewing tasks, submitting 
    waste cleanup reports, joining cleanup drives, and redeeming rewards.
- Created data_store.py to manage tasks, announcements, 
    waste reports, and cleanup drive information.
- Improved the interaction between the admin and volunteer 
    dashboards to support the main waste management functions.
- Identified issues that still need improvement, including 
    cleanup drive participation not appearing correctly in the task display.
- Started developing the rewards system, although the points 
    system and redemption process still need further improvements.
- Continued improving the dashboard design and functionality 
    in preparation for the next development phase.


Progress 3: Volunteer Profile and Account Management Features - ASAJAR

- Added a View Profile section where volunteers can view their personal 
and demographic information.
- Added an Edit Profile feature for updating personal details, contact information, 
and emergency contact information.
- Implemented profile picture uploading and saving to the system.
- Added a Valid ID Upload feature to allow volunteers to submit an identification 
document for future identity verification.
- Added a Gallery feature for viewing images uploaded with waste reports.
- Developed a Recent Posts feature for viewing previously submitted waste reports, 
including available images, descriptions, locations, and submission dates.
- Added a Delete Account feature that requires password confirmation to prevent 
accidental account deletion.
- Implemented a Change Password feature that verifies the current password before 
saving a new password securely.
- Added an Achievements section as a placeholder for the future volunteer points 
and badge system.
- Updated the account model and account-saving functionality to support additional 
profile information.
- Improved volunteer account management and prepared the system for future enhancements, 
including persistent report history, identity verification, and a fully functional achievements and rewards system.


Progress 4: Admin Pointing Distributions and Viewing of Points - URBANO
- Added a new feature to the volunteer dashboard for viewing the volunteer's available points.
- Added a new feature to the admin dashboard that allows administrators to distribute 
    points to volunteers.
- Administrators can select a volunteer's username before assigning points.
- Updated the Rewards section to display the volunteer's total points at the top.
- To be added: Level multipliers and reward costs.
- The progress is not yet final.


Progress 5: Points System Integration, Reward Redemption, and System Enhancements – MAPAS, RAMOS
- Updated the admin dashboard buttons to match the design and style of the volunteer dashboard.
- Added the ability for administrators to update the status of redeemed items and delete 
    redemption records.
- Added a notification-clearing feature that removes notifications only for the account that 
    clears them, keeping each user's notification data separate.
- Implemented automatic point deduction when a volunteer redeems a reward.
- Added data persistence so user information and application data are retained when the 
    program is closed and reopened.
- Reduced the number of available reward items temporarily for testing purposes.
- Added the ability for administrators to delete tasks and waste reports.


Progress 6: Application Icon, Cleanup Drive Scheduling, Task Management, and Progress Tracking – MAPAS, RAMOS, URBANO
- Added application icon files and updated main.py to set the application window icon.
- Added a Cleanup Schedules section to the Admin Dashboard, allowing administrators to create, publish, view, 
    and delete cleanup drive schedules.
- Improved volunteer task management by adding the Join Task, Mark as Done, and Clear Completed Task functions.
- Added task participation and completion records, including timestamps, to the persistent data store.
- Updated the circular progress indicator to calculate the percentage of completed tasks instead of displaying 
    a fixed percentage.
- Connected cleanup drive participation to the volunteer task list so that joining a cleanup drive automatically 
    adds its corresponding task.
- Added styling for selected list items to improve text readability and selection appearance.
- Extended data_store.py to save and load volunteer task participation and cleared-task records.


Progress 7: Forgot Password, Email Integration, and Account Email Support – PELLAZAR
- Added a Forgot Password option to the login interface, allowing users to open a password-reset page without 
    leaving the login window.
- Added a password-reset service that generates a six-digit verification code and sends it to the registered 
    email address through SMTP.
- Implemented verification-code checking and password updating, including saving the updated password hash 
    and salt to the account data.
- Added an email-address field to the volunteer registration interface.
- Updated account registration to check for duplicate usernames and email addresses.
- Extended the account model and serialization logic to store and retrieve email addresses.
- Added a background email-sending thread to avoid performing SMTP operations directly on the main GUI thread.


Progress 8: System Notification and Email Announcements - PELLAZAR

- Added an email notification feature that allows administrators to send system announcements directly 
    to registered volunteers.
- Improved the notification process so announcements can be sent through email without freezing the 
    application interface.
- Added success and failure messages to inform administrators about the result of email delivery.
- Connected email announcements with the existing notification system so announcements are saved 
    and can still be viewed within the application.
- Improved the communication between administrators and volunteers by providing email notifications 
    for important system announcements.