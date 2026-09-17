# Creator Research Agent

## Purpose

This project researches publicly available information about
content creators, particularly creators involved in AI, software,
technology, and AI-generated content.

The goal is to discover relevant creators, collect publicly
available information, analyze their content, and maintain
structured research records.

## Behaviour

- Be methodical and evidence-driven.
- Never invent creator information.
- Treat missing information as unknown.
- Prefer primary/public sources.
- Record the source URL for important information.
- Clearly distinguish discovered facts from AI inference.
- Validate data before writing it to the final dataset.
- Reuse existing Python scripts when appropriate.
- Improve existing scripts rather than unnecessarily rewriting them.
- Keep the project organized.

## Research

When researching creators:

1. Discover potential creators.
2. Verify that the creator is relevant.
3. Visit available public sources.
4. Extract publicly available information.
5. Normalize the information.
6. Record evidence.
7. Analyze relevance.
8. Store the result.

## Data Quality

See AGENTS.md for detailed data quality rules.

## Coding

Primary languages:
- Python
- TypeScript

Prefer:
- readable code
- modular code
- reusable functions
- error handling
- logging
- deterministic extraction

Do not modify working code unnecessarily.

Before changing a scraper:
1. inspect the existing implementation
2. understand the failure
3. make the smallest appropriate change
4. test the change
5. verify the output

## Output

Structured datasets should normally be stored as:

CSV:
`data/output/`

JSON:
`data/output/`

## Security

Never expose API keys, credentials, cookies, session tokens,
or other secrets in notes, CSV files, Git commits, or responses.
