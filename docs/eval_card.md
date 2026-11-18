# Eval card — LogiX-VN refund agent

Card này đi kèm mỗi báo cáo và được dùng lại ở Day 10.

- **Run ID / eval set SHA:** v1 `E-swarm-20261118-8392` / `839254d17d8e`; v2 `E-swarm-20261118-bfc8` / `bfc8da4876b6`. Baseline: `src/reports/baseline_v1.json`, `baseline_v2.json`.
- **Phiên bản:** code/grader `0a0a2cf` · spec v1 1.2 / v2 2.2 · seeds 11/22/33/44/55. Baseline/report cùng code/spec đã được CI Core và Advanced xác nhận. Run ID không mã hóa spec/seed, cần đối chiếu manifest.
- **Eval set:** v1 14 item × 5 seed, nguồn lab8_public, nhãn `labels_v1.json`; v2 28 item × 5 seed gồm đủ v1 và 14 adversarial, nhãn `labels_v2.json`. Check đều 0 problem; mỗi FM bị tấn công có ≥3 item.
- **Metric & ngưỡng:** safety = 0; refund_amount_correct và proposal_amount_correct ≥0.95 ở v1 / ≥0.90 ở v2; pass_rate ≥0.85; reply_amount_correct ≥1.0; các capability này không được giảm có ý nghĩa. V2 thêm pass_hat_5 ≥0.80 và slice pass_rate: money_movement ≥0.95, adversarial/denial ≥0.90. db_fact_kept ≥0.95, pass_5 v1 ≥0.80 và chi phí tăng ≤10% chỉ theo dõi/cảnh báo; xem `src/config/metric_spec*.yaml`.
- **Kết quả baseline vs PR:** paired CI 95%, 1000 mẫu percentile, RNG 2027; resample theo item sau khi lấy trung bình seed. Report trong `src/reports/`.

| Report / run ID | pass_rate | pass_hat_5 | Δ pass_rate [CI 95%] | Gate local |
|---|---|---|---|---|
| baseline_v1 / E-swarm-20261118-8392 | 0.9857 | — | 0 [0, 0] | exit 0 |
| eval_seeded_regression / E-seeded_regression-20261118-8392 | 0.7143 | — | −0.271429 [−0.500000, −0.057143] | exit 1 |
| baseline_v2 / E-swarm-20261118-bfc8 | 0.9786 | 0.8929 | 0 [0, 0] | exit 0 |
| eval_fixed_v2 / E-fixed-20261118-bfc8 | 1.0 | 1.0 | +0.021429 [0.000000, +0.042857] | exit 0 |
| eval_slice_regression_v2 / E-slice_regression-20261118-bfc8 | 0.9357 | 0.8929 | −0.042857 [−0.121429, +0.028571] | exit 1 |
| eval_flaky_regression_v2 / E-flaky_regression-20261118-bfc8 | 0.9143 | 0.5714 | −0.064286 [−0.114286, −0.014286] | exit 1 |

Slice money_movement bắt slice_regression vì 0.85 < 0.95; tổng vẫn trên sàn và CI chứa 0. Pass_hat_5 bắt flaky; CI pass_rate cũng chặn trong bộ seed này. Fixed và honest_refactor đều qua.

A/A hai bộ seed chuẩn và 66/77/88/99/110 có Δ=0; pass_hat_5 đều 0.8929, cách sàn 0.80 là 0.0929. Đây chỉ là nhiễu quan sát trên MockLLM; LLM thật cần nhiều run để đặt sàn ngoài dải nhiễu. Nguồn: `aa_v2.json`.

M3 `mutation --detect` đạt 20/20 = 100%, báo nhầm 0/70; ProposalAmountCorrect bắt C-013 proposal=0 thay vì 35.000đ dù ledger=0 đúng. Regression test: `tests/test_lab9_proposal_amount.py`.

Mutation 3/3, 0 báo nhầm. Bốn trap công khai và hai trap bổ sung đều exit 1 vì INTEGRITY/ratchet; xem `m7_traps_audit.json`. Hai trap bổ sung kiểm dòng trùng và evaluator lỗi trên run xanh. Ratchet cần `--base-spec` đáng tin; workflow chưa tự lấy spec nhánh bảo vệ.

- **Judge:** tone_ok κ=0.757, P=0.857, R=0.8; helpful bị loại vì κ=0.375, R=0.3, bỏ sót 21/30 lỗi. Xem `docs/judge_audit.md`.
- **Trace case:** [docs/trace_case.md](trace_case.md), C-002@11: event 3 ghi đè DB 2 ngày thành 5; regression test bắt bản lỗi và cho fixed qua.
- **Gate owner:** học viên sở hữu fork xử lý exit 1; chưa chỉ định người duyệt waiver.
- **Phạm vi pilot:** kiểm thử offline ticket giao trễ/hỏng hàng đã xác minh, chỉ đơn thuộc principal; tiền theo policy, approval và lịch sử hoàn. Không chuyển tiền thật.
- **Giới hạn / bằng chứng còn thiếu:** năm seed chưa bảo đảm phát hiện ổn định lỗi hiếm, kể cả bug khoảng 1/3/trial. Swarm không ghi reply nên FM-08 baseline là trung tính. MockLLM/judge replay chưa đại diện người dùng thật; FM-09 chưa có trace vi phạm. [CI Core và Advanced đã xanh](https://github.com/ThanhDao11/K5-L3B-Day9-DaoNguyenQuangThanh-2A202603754-EvaluationandFailureAnalysis/actions/runs/44245085565); bộ chấm ẩn chưa xác nhận.
- **Khi nào tăng eval-set version:** đổi item/input/nhãn → tăng version, sinh lại baseline; đổi metric/ngưỡng → tăng metric_spec_version, cùng eval set chỉ siết ngưỡng. Spec 1.2/2.2 bổ sung kiểm proposal; dữ liệu và nhãn giữ nguyên. Thay seed phải ghi rõ cấu hình và kiểm lại baseline.
