# Bài B: người canh, phần kiểm bằng code

- Ngày: 2026-10-19
- Commit: `b1a80f66287a43afc4b03e3612f32af7d7280f28`
- Hash đầu vào (sha256, 16 ký tự đầu): `3f9ece7cc30feef6` của evals/scenarios/guard-b/cases.yaml, config/guard.yaml, data/sample-story/graph.yaml
- Model: không dùng model (phần kiểm bằng code)
- Lệnh: `cd backend && uv run python -m writory.guard.bench_b --out <thư mục này>`

| Phép kiểm | Ca lỗi | Bắt được | Recall | Ca sạch | Báo nhầm |
|---|---|---|---|---|---|
| chapter_rule | 2 | 2 | 100% | 2 | 0 |
| dead_actor | 3 | 3 | 100% | 3 | 0 |
| at_most_one | 3 | 3 | 100% | 4 | 0 |
| teller_does_not_know | 2 | 2 | 100% | 3 | 0 |
| early_reveal | 2 | 2 | 100% | 3 | 0 |
| sudden_relationship | 2 | 2 | 100% | 5 | 0 |

Loại lỗi báo ngoài `expect` (mọi ca): 0
