# Acceptance Scenarios (Gherkin-style)

### Portfolio review
Given the 25 demo hotels and a specialist assigned to all of them
When an AI host calls `ads.list_managed_hotels` and `growth.audit_portfolio`
Then 25 unique hotel IDs are included, alerts have rule/evidence fields, and no live ad mutation is attempted.

### Historical campaign economics
Given Kyoto Campaign A: spend 100k, 8×40k bookings, 4 cancellations; and B: spend 100k, 6×50k, 0 cancellations
When `growth.calculate_campaign_economics` executes with variable cost ratio .30
Then gross ROAS A=3.2 and B=3.0; contribution A=12,000 and B=110,000 JPY; no causal lift claim is made.

### Approval state machine
Given pending proposal for Kyoto shifting 30,000 JPY A to B
When execution is called before approval
Then it is denied and no budgets change.
When an authorized specialist explicitly approves and `ads.execute_mock_reallocation` runs
Then the campaign monthly budgets become 70,000 and 130,000 JPY and an audit event is persisted.
When the same idempotency key is called again
Then no additional mutation occurs.

### Authorization and budget policies
Given an actor not assigned to Kyoto
When they try approving or executing the Kyoto proposal
Then policy denies.
Given a cross-hotel source/destination or amount above remaining budget
When a proposal is requested
Then tool returns validation error; no proposal becomes executable.

### Reports and reproducibility
Given a fixed data reset and an audit for September 2026
When report generator runs twice
Then both reports contain the same numeric values and are explicitly marked DEMO DATA.
