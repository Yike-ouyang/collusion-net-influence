# Related work and positioning

This is a focused starting bibliography, not an exhaustive novelty search.

| Work | What it establishes | Relation to this study |
|---|---|---|
| Zou et al. (2023), [Universal and Transferable Adversarial Attacks on Aligned Language Models](https://arxiv.org/abs/2307.15043) | GCG searches discrete suffix tokens using gradients and greedy candidate evaluation; the objective targets a desired response over prompts. | The optimization tool is established. This project changes the target to channel/no-channel policy matching and later behavioural outcomes. |
| Liu et al. (2025), [Can an Individual Manipulate the Collective Decisions of Multi-Agents?](https://aclanthology.org/2025.emnlp-main.611/) | M-Spoiler optimizes adversarial suffixes to influence collective multi-agent decisions and uses multiple simulated dialogue turns in its objective. | Closest methodological precedent. It manipulates collective decisions; this project asks whether a suffix can reduce channel-associated coordination in repeated games. |
| Bonjour, Aggarwal & Bhargava (2022), [Information-Theoretic Approach to Detect Collusion in Multi-Agent Games](https://proceedings.mlr.press/v180/bonjour22a.html) | Mutual information between actions can be a useful collusion signal in repeated games. | Motivates action-dependence outcomes. It does not make prompt-policy KL a direct CMI estimator. |
| Fish, Gonczarowski & Shorrer (2024), [Algorithmic Collusion by Large Language Models](https://arxiv.org/abs/2404.00806) | LLM pricing agents can produce supracompetitive outcomes, and small prompt changes can alter them. | Supports prompt sensitivity as a relevant intervention axis, but studies pricing outcomes rather than a GCG anti-coordination suffix. |
| Garra (2026), [Mitigating Emergent Collusion in LLM Pricing Agents](https://arxiv.org/abs/2609.13037) | A prompt-only warning partially reduces above-Nash pricing in a repeated pricing experiment; payoff and market-structure changes have stronger effects in that study. | Directly motivates the natural-language counterinstruction comparison. Treat as a recent preprint. |
| Nakamura et al. (2026), [Colosseum: Auditing Collusion in Cooperative Multi-Agent Systems](https://arxiv.org/abs/2602.15198) | Separates collusive plans in text from collusive actions and outcome effects. | Motivates reporting messages/plans, actions, and payoffs as separate evidence. |

## Narrow contribution to test

The plausible contribution is not “GCG for suffixes” or “collusion in LLMs” alone. It is a combination of (i) a no-channel reference policy objective, (ii) independent chronological suffix updates per complete run, (iii) held-next-block replay evaluation, and (iv) new-game behavioural validation against a direct instruction and placebo suffixes. The replay pilot is not enough to claim that a suffix reduces collusion: only fresh complete-game outcomes can support that claim.
