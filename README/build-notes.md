# Build notes:

# As of 10/6:
- Flushed DB due to model updates:
- Created a prospect, updated prospect detail, updated status with note, converted prospect, created draft, updated draft, sent for approval, approved, converted to proposal, able to regenerate proposals as well.

# As of 10/3:
- Redirect links for adding staff users and updating staff.  No custom pages for this just over to admin

# As of 10/2:
- Add Prospect
- Update Prospect
- Change status of Prospect to include updating to a won which will then convert the prospect to not a client but a company
- Add Company
- Contacts Admin page 
    - View Prospective clients (all status but won lost or dnc) and can view their page and update and edit ** need to make sure that when adding a note in new section on update details that it saves to the prospectNote table right now it is not saving anywhere.
    - View won Prospects - these are now companies but not a user based client so still in proposal step
    - View current clients - These have accounts in system
    - View DNC clients
    - View lost clients - and view their page
- Company Admin page
    - View Prospects (same as above but not the DNC, WON, or Lost) and can view their page
    - Companies all including just won but those should keep client status of converted till the have an account - can view their pages
- Proposal Admin
    - Drafts - can view each one has logic to approve and convert but may be broken
    - Proposals
- Invoice Admin
    - Open
    - Paid
- Team Admin
    - List of staff based users - can view each one