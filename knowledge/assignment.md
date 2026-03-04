# Alma Lead Management — Take-Home Assignment

## Assignment

### Functional Requirements

Develop an application to support creating, getting and updating leads. A lead is a form PUBLICLY available for prospects to fill in, the required fields include:

- first name
- last name
- email
- resume / CV

Once the lead is submitted by a prospect, the application will send emails to both the prospect and an attorney inside the company.

In addition, the application powers an internal UI guarded by auth to render a list of leads with all the information filled in by the prospect. Each lead also has a state, it starts with a **PENDING** state and transitions to **REACHED_OUT** when marked manually by an attorney after he / she reaches out to the prospect.

### Tech Requirements

- Create a system design to fulfill the above requirements
- Implement all APIs needed to fulfill the above requirements (there is no need to develop UI)
- Use FastAPI to implement the application
- Add a storage to persist data
- Properly structure the code similar to how you would for a production level repo

### Submission Guidance

- Submit your code to a publicly available github repo
- Submit a document on how to run your application locally in the same repo
- Submit a design document on why/how you make those design choices in the same repo
- Any additional documents that could help us understand the application better in the same repo
- Upload the github link in the assignment document within 6 hours since you start the exercise
