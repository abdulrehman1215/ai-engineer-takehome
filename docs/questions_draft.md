# Questions for the hiring team

Each question comes with the assumption I made so I could carry on without an answer.

| # | Question | Assumption I made | If it is wrong |
|---|---|---|---|
| 1 | Can the Hearth Workspace contract still be changed? It renews each year unless notice comes 14 days before the renewal date, and 36 of 240 seats are active. | Yes. I recommend serving notice or cutting seats, and I do not treat the renewal as already locked in. | If it has renewed, the saving moves to the next term and falls outside the 12 months. |
| 2 | Will unseen data keep the sample's file names and columns? | The names and columns stay the same and only the rows and values change. A changed structure stops the run with an input error, and a bad row is set aside and blocks only its own invoice. | A new layout needs a mapping step. That belongs in the 30-day plan, not in the slices. |
| 3 | Which AI provider, and what budget, may touch client data? Northgate's Schedule 4 lists none. | None. Neither slice calls a model. Anything that sends client text to a model waits for a Schedule 4 listing or written client approval. | If a provider is approved, the HR and consulting text work becomes possible. The finance and engineering slices stay the same. |
| 4 | Is revenue recognised evenly over a contract's delivery months, and is there a utilisation figure for consultants? | Revenue is recognised evenly from signature, and there is no data on capacity. So the $125k verdict rests on win-rate arithmetic alone, and it says so. | If recognition comes late in a contract, extra wins add less revenue in the first year and $125k is further out of reach. |
| 5 | Who can own AI spend and the data-handling rules? | The CEO's office names one owner in the first week. I can recommend an owner but I cannot assign one. | Without an owner, none of the controls in the 30-day plan will hold. |
| 6 | Is the second approval from the security group (clause 2) recorded anywhere? | The sample logs only the first reviewer. I treat `auth-service` and `patient-records` as the services that need the second approval. | If the real scope is narrower, the strict tier is too wide. If it is wider, the tier misses changes. |
| 7 | Which services are Schedule 2 client environments? | None are listed. The triage reads metadata only and never code, so those repositories can be included safely. A config setting marks them. | If code content is needed later, those repositories stay away from any external service. |
