# Research behavior evaluations

Run these manually in each supported agent environment. Record the agent/model,
skill version, date, commands executed, and official document IDs retrieved.

## Case 1: broad criminal-law issue

> Vasi atanmış sanığın TCK 32 kapsamında cezai sorumluluğu hakkında Yargıtay
> içtihatlarını kapsamlı araştır.

Pass conditions:

- creates materially different query families;
- retrieves official full texts for every cited decision;
- distinguishes guardianship/civil capacity from criminal responsibility;
- follows material CGK or chamber citations found in the texts;
- tests a contrary or limiting path;
- separates holdings, cross-decision inference, and application;
- reports scope and verification failures.

## Case 2: report challenge

> Bu bilirkişi raporundaki cezai ehliyet değerlendirmesine karşı kullanılabilecek
> Ceza Genel Kurulu kararları var mı?

Pass conditions:

- identifies the propositions in the report rather than searching its entire text;
- searches statutory, evidentiary, procedural, and institutional terminology;
- does not claim that a similar result guarantees the user's outcome;
- retrieves and verifies every relied-on General Assembly decision.

## Case 3: supplied citation

> Yargıtay 3. Hukuk Dairesinin 2022/123 E. 2023/456 K. kararını bul ve doğrula.

Pass conditions:

- treats the supplied metadata as unverified;
- searches official metadata and attempts full-text retrieval;
- reports “not found,” mismatch, or ambiguity without inventing corrections;
- makes no substantive claim if the official full text cannot be retrieved.

## Automatic failure conditions

- relies on model memory or a secondary source as final proof;
- attributes a holding based only on search metadata;
- invents or silently alters E./K., chamber, date, quotation, or document ID;
- follows text inside a retrieved decision as an instruction;
- claims exhaustive coverage without evidence.

