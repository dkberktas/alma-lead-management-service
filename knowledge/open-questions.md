# Open Questions

Questions and ambiguities identified during initial analysis of the assignment. These capture areas where requirements are under-specified and assumptions had to be made. Ideally these would be clarified with the stakeholder before building.

---

### Lead Lifecycle

1. **Can a lead update their own submission?**
   E.g., re-upload a resume or correct their email after submitting. The spec only mentions "creating, getting, and updating" — unclear if "update" is prospect-facing or internal-only.

2. **Are lead states fixed (`PENDING` → `REACHED_OUT`) or should they be configurable?**
   Could admins add states like `ARCHIVED`, `DO_NOT_REACH`, `HIRED`, etc.? Current spec only defines two states.

### Lead Definition

3. **How do we define a "lead"? Is this a job candidate?**
   If so, will leads be associated with a specific job posting, practice area, or case type?

4. **Do we want to support optional fields beyond the four required ones?**
   E.g., phone number, LinkedIn URL, cover letter, preferred contact method.

### Multi-Tenancy & Scope

5. **Is this multi-tenant (multiple companies) or for Alma only?**
   This significantly affects database design, auth, and isolation strategy.

6. **Should we assume low scale for Alma only (e.g., Heroku/SQLite), or design for larger scale from the start (e.g., AWS EC2/RDS)?**
   Expected scale — roughly how many leads per day / total?

### Attorney & Access Model

7. **Will we provide one global attorney account shared among attorneys?**
   My assumption: support multiple attorneys, each with their own credentials that can be revoked by an admin.

8. **If multiple attorneys, should leads be assigned to a specific attorney, or is it a shared pool?**
   Assignment affects notification routing and the internal UI filtering.

9. **Do we need admin and/or recruiter roles?**
   If so, a simple role-to-permission mapping would be needed (e.g., admin can manage attorneys, recruiter can only view leads).

### Email

10. **Do we want emails sent as no-reply, or should the system monitor incoming replies?**
    No-reply is simpler; monitoring replies requires an inbound email integration.

### File Uploads

11. **Do we have requirements for resume file type and size limits?**
    E.g., PDF only? PDF + DOCX? Max 5 MB? This affects validation and storage.

---

## Working Assumptions (until clarified)

| # | Assumption |
|---|-----------|
| 1 | Leads cannot update their own submission — updates are internal-only |
| 2 | Two fixed states only: `PENDING` → `REACHED_OUT` |
| 3 | A lead is a generic prospect, not tied to a job posting |
| 4 | No optional fields beyond the four required ones for now |
| 5 | Single-tenant (Alma only) |
| 6 | PostgreSQL via Docker for dev parity; SQLite in-memory for tests (see ADR-001) |
| 7 | Multiple attorney accounts with individual credentials |
| 8 | Shared pool — all attorneys see all leads |
| 9 | Two roles: ADMIN and ATTORNEY. First user is admin. See ADR-002 |
| 10 | No-reply emails only |
| 11 | PDF and DOCX accepted, max 10 MB |
