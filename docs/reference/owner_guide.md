# Owner's Guide

## What NBA Tools is for

Type an NBA statistics question naturally and get the answer you asked for:
the right players or teams, the right statistic, the right time period, and all
meaningful conditions included. The webpage should show the result clearly.

The product direction is in [the roadmap](../../ROADMAP.md). The
[query catalog](query_catalog.md) describes verified current support, not the
limit of what agents should build next.

## Your role

You steer the product. You do not have to understand its backend, write test
cases, verify arithmetic, select technical tasks, or coordinate reviewer
handoffs. You can contribute examples at any time; agents own investigating
and implementing them. You do not have to supply examples for work to proceed.

Agents should ask you only for genuinely unresolved product choices, necessary
account access or consent, meaningful new spending, or consequential actions
outside authorization. They should bring a recommendation with the question.

## How the app works

The webpage sends the question to the shared engine. The engine identifies the
subject, statistic, period, and conditions, chooses the appropriate calculation,
loads the configured NBA data, and computes an answer. The webpage displays it.
The API and development command-line tool use that same engine.

When something fails, agents determine whether the missing piece is language
understanding, data, calculation, or display. That diagnosis is not your job.

## What progress should look like

An update should tell you what now answers correctly, what remains unfinished,
how the answer was verified, what happens next, and whether anything is needed
from you. Technical receipts belong in the associated change record.

A desired question that the tool cannot answer is unfinished. A safer rejection
can prevent misinformation while work continues, but it does not deliver the
feature. Invalid questions and genuine ambiguities are tested separately. A
verified answer of zero or no matching games can be completely correct.

## What the testing is for

Agents use sample questions to discover gaps, numerical checks to verify
answers, regression tests to prevent breakage, and browser checks to inspect
what users see. They should test unfamiliar wording as well as known examples.
A large passing test count is not a count of useful answered questions.

Existing reports may use terms such as `human_review_pending`. Those labels do
not turn routine technical verification into an assignment for you. Agents must
record their own verification honestly, without claiming you reviewed anything
you did not. Product branding and launch choices remain yours.

The [agent instructions](../../AGENTS.md) and
[feature delivery rules](../operations/feature_promotion_rules.md) define this
division of responsibility. You do not need to learn their commands to own the
project.
