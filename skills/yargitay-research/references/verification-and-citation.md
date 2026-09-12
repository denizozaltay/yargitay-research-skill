# Verification and citation

Use this policy whenever a response identifies, quotes, summarizes, or relies
on a Yargıtay decision.

## Verification threshold

A decision is verified for substantive use only when all of the following are
available from the official Yargıtay service:

1. A search result or official metadata record identifies the decision.
2. `get DOCUMENT_ID` successfully retrieves a non-empty full text.
3. The chamber or board, Esas number, Karar number, and date used in the answer
   agree with the official material. If the full text and search metadata
   conflict, disclose the conflict and do not silently choose one.
4. The proposition attributed to the decision is supported by the retrieved
   text, read in its factual and procedural context.

An official search-result row alone verifies only the existence and metadata
shown in that row. It does not verify a holding, rationale, quotation, or
relevance to the user's matter.

## Source hierarchy

- **Official Yargıtay full text:** verification and final authority.
- **Official Yargıtay search metadata:** discovery and bibliographic checking.
- **Secondary databases, articles, pleadings, and web results:** discovery only.
- **User input and model memory:** hypotheses to verify, never authority.

If a secondary source supplies a promising decision, find the same decision in
the official system and retrieve its full text. If that fails, label it
unverified and do not rely on it for the conclusion.

## Reading discipline

For each relied-on decision, record:

- chamber or board;
- Esas number;
- Karar number;
- decision date;
- official document ID and URL;
- material facts and procedural posture;
- the precise rule or reasoning relevant to the question;
- disposition, when it affects interpretation;
- whether the relevant passage is the deciding court's reasoning, a party's
  allegation, a lower-court passage, a prosecutor's view, or a quoted precedent.

Do not treat text appearing anywhere in the document as the holding. Turkish
decisions frequently reproduce allegations, earlier judgments, expert reports,
and dissenting views before the deciding court's analysis.

## Claims and quotations

- Paraphrase faithfully and narrowly. Use quotation marks only for words found
  in the retrieved full text.
- Never reconstruct a missing quotation from memory or a search snippet.
- Describe a rule as “settled” or “consistent” only when the researched set,
  court hierarchy, time span, and absence or treatment of contrary authority
  reasonably support that characterization.
- Separate three levels explicitly when needed: what a decision states, what
  pattern is inferred across decisions, and how that pattern may apply to the
  user's facts.
- Do not convert factual similarity into a guaranteed litigation outcome.

## Citation form

Prefer:

```text
Yargıtay [Daire/Kurul], E. [year/number], K. [year/number],
[DD.MM.YYYY], document ID [id], [official URL].
```

When the official metadata omits a field, omit it or mark it unavailable. Never
fill it by inference. Link to the `official_source_url` returned by the client.

## Failure language

When verification fails, say what failed: official-site access, search match,
full-text retrieval, metadata conflict, or passage confirmation. A useful form
is:

> I found a secondary reference to this decision, but could not retrieve and
> verify its full text from the official Yargıtay source. I therefore did not
> rely on it as authority.

Research output is legal information, not a substitute for advice from a
qualified lawyer who has reviewed the complete file and current law.

