# Judge audit

Chạy từ `src/`: `python -m lab9.judge --csv data/eval/judge_tone_public.csv --audit 5`; thay bằng `judge_helpful_public.csv` để kiểm helpful. `FAIL` là lớp dương.

| Tiêu chí | n | κ | Precision | Recall | Đạt FLOORS (κ≥0.6, P≥0.8, R≥0.7)? | Quyết định |
|---|---|---|---|---|---|---|
| tone_ok | 100 | 0.757 | 0.857 | 0.800 | Có | dùng cho giọng điệu |
| helpful | 100 | 0.375 | 1.000 | 0.300 | Không | loại khỏi gate |

## ≥5 case audit thủ công

| # | Case | Judge nói | Người nói | Ai đúng? | Ghi chú |
|---|---|---|---|---|---|
| 1 | H-008 | PASS | FAIL | Người | “Em… nha… anh check” suồng sã theo chuẩn CSV; thêm ví dụ xưng hô phù hợp. |
| 2 | H-017 | PASS | FAIL | Người theo note | “Bạn ơi… nha” không hợp ngữ cảnh khách lớn tuổi; cung cấp context, không yêu cầu judge đoán tuổi. |
| 3 | H-029 | PASS | FAIL | Người | “Không cần nhắn thêm” mang giọng ra lệnh; chấm cả câu, không chỉ từ “Dạ”. |
| 4 | H-042 | FAIL | PASS | Người | Câu ngắn nhưng đủ ý; không bắt buộc xin lỗi trong mọi tình huống. |
| 5 | H-051 | FAIL | PASS | Người theo note | “Refund” được CS cho phép; thêm thuật ngữ hợp lệ vào rubric. |
| 6 | HL-016 | PASS | FAIL | Người theo note | Reply 55.000đ, ledger ghi 35.000đ; lời xin lỗi dài không bù sai tiền, chuyển kiểm tiền sang code. |

## Kết luận

- Tone: TP/FP/FN/TN = 24/4/6/66, đạt sàn. Helpful: 9/0/21/70, bỏ sót 21/30 lỗi nên không dùng làm gate dù precision=1.0.
- Rogan–Gladen: tỉ lệ lỗi quan sát tone 0.28, helpful 0.09; đều hiệu chỉnh thành 0.30. Hiệu chỉnh tỉ lệ tổng không sửa từng verdict hoặc làm helpful đạt calibration.
- Rủi ro còn lại: CSV replay công khai, ghi chú ledger chưa kiểm chứng độc lập; cần nhãn người mới và held-out sau khi sửa rubric. Tiền/approval chấm bằng code, không dùng judge.
