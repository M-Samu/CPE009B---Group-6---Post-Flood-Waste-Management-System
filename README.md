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