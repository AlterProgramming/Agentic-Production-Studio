# Creative Model Evaluation Workflow

## 1. Define the production task

- Exact output type
- Required style consistency
- Reference-image behavior
- Resolution and latency needs
- Batch volume
- Rights and privacy constraints

## 2. Select candidates

Record:

- Model name and version
- License
- Hosting requirements
- Adapter compatibility
- Expected cost
- Known limitations

## 3. Build the test set

- Representative prompts or inputs
- Edge cases
- Negative cases
- Style references
- Fixed seeds when supported
- Human-review rubric

## 4. Evaluate

Score:

- Prompt adherence
- Reference adherence
- Temporal or multi-frame consistency
- Anatomy and object integrity
- Palette and outline stability
- Editability
- Latency
- Cost
- Failure rate

## 5. Adapter or configuration experiment

Run only when:

- Base-model performance is close to acceptable
- Training or reference rights are clear
- Improvement can be measured against the same test set

## 6. Deployment decision

Choose:

- Reject
- Use hosted API
- Deploy private endpoint
- Use batch Jobs workflow
- Continue adapter research

## 7. Delivery

- Benchmark report
- Raw result index
- Model card
- Configuration
- Cost model
- Deployment instructions
- Provenance and license record
