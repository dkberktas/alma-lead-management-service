- how do we define a lead? is this a job candidate? If so, will we associate these to a job posting as well?
A lead is someone who is interested in using our immigration service 
- is this multi-tenant, multiple companies can use this or for Alma only?
This is for Alma. 
- will we provide one global attorney account that will be shared among existing attorneys? (My assumption
was to support multiple attorneys, each has their own access that can be revoked by admin)
Yes to support multiple attorneys 
- are lead states fixed (pending, reached_out) or should the states be configurable by admin (adding a new role as archieved, do_not_reach, etc)?
For now, we could keep them fixed. 
- do we need admin and/or recuiter role? (If so, maybe a simple role to permission mapping)
It's nice to have. 
- do we want emails to be send as a no-reply meaning should the system monitor incoming replies?
I am not sure if I understand fully. If you are asking whether we should monitor replies through emails, I say it's nice to have. 
- if multiple attorneys, should leads be assigned to a specific attorney, or is it a shared pool?
We could assume that this is manually assigned to start with. 
- expected scale? Roughly how many leads per day / total?
Your call. 
- do we have a requirement for resume file type (pdf, md, txt) and size limits?
Your call. 
- should we assume low scale for Alma only (e.g., Heroku/Supabase etc), or design for larger scale from the start (e.g. AWS EC2/RDS)?
Your call. 
- do we want to dedupe based on email to track multiple applications/history?
Your call. 