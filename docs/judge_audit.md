# Judge audit

Chạy từ `lab9/src/`, đã kích hoạt `.venv`:

```powershell
python -m lab9.judge --csv data/eval/judge_tone_public.csv --audit 5
python -m lab9.judge --csv data/eval/judge_helpful_public.csv --audit 5
```

Backend là replay, không gọi LLM thật. `FAIL` là lớp dương: TP là judge tìm đúng lỗi; FN là bỏ sót lỗi. Mọi số dưới đây lấy từ output calibration trên CSV công khai, không phải đo trên người dùng thật.

| Tiêu chí | n | κ | Precision | Recall | Đạt FLOORS (κ≥0.6, P≥0.8, R≥0.7)? | Quyết định |
|---|---|---|---|---|---|---|
| tone_ok | 100 | 0.757 | 0.857 | 0.800 | Có | Dùng cho giọng điệu trong phạm vi đã calibration |
| helpful | 100 | 0.375 | 1.000 | 0.300 | Không: κ và recall dưới sàn | Loại khỏi gate |

| Tiêu chí | TP | FP | FN | TN | Tỉ lệ lỗi judge quan sát | Rogan–Gladen hiệu chỉnh | CLI exit |
|---|---:|---:|---:|---:|---:|---:|---:|
| tone_ok | 24 | 4 | 6 | 66 | 0.280 | 0.300 | 0 |
| helpful | 9 | 0 | 21 | 70 | 0.090 | 0.300 | 1 (đúng kỳ vọng) |

Precision cao của helpful không bù được việc bỏ sót: nó chỉ phát hiện 9/30 lỗi. Rogan–Gladen sửa ước lượng tỉ lệ lỗi tổng thể bằng sensitivity/specificity; không sửa từng verdict và không biến judge không đạt thành judge đủ điều kiện làm gate. Trên cùng tập calibration, tỉ lệ hiệu chỉnh khớp 30/100 nhãn FAIL của người là nhất quán đại số, không phải bằng chứng tổng quát hóa.

## ≥5 case audit thủ công
| # | Case | Judge nói | Người nói | Ai đúng theo bằng chứng công khai? | Bằng chứng và hành động sửa rubric |
|---|---|---|---|---|---|---|
| 1 | tone H-008 | PASS (FN) | FAIL | Người, theo chuẩn xưng hô ghi trong note | Reply dùng “em”, “nha”, “anh check”. Thêm ví dụ phân biệt thân thiện và suồng sã; yêu cầu xưng hô theo chuẩn CS đã thống nhất. |
| 2 | tone H-017 | PASS (FN) | FAIL | Người theo note khách lớn tuổi; reply riêng không chứng minh tuổi | “Bạn ơi … rồi nha” không phù hợp ngữ cảnh ghi trong note. Rubric cần context xưng hô hoặc chuẩn mặc định anh/chị; không yêu cầu judge đoán tuổi từ reply. |
| 3 | tone H-029 | PASS (FN) | FAIL | Người | “Không cần nhắn thêm” mang giọng ngăn cản khách. Không tự động PASS vì có “Dạ, vui lòng”; chấm cả câu và cách hướng dẫn bước tiếp theo. |
| 4 | tone H-042 | FAIL (FP) | PASS | Người | Reply ngắn, lịch sự, có kết quả và thời gian tiền về. Không bắt buộc câu xin lỗi trong mọi tình huống; không phạt độ ngắn khi đủ ý. |
| 5 | tone H-051 | FAIL (FP) | PASS | Người theo note về từ vựng CS LogiX | Từ “refund” được chấp nhận trong dữ liệu chuẩn. Thêm danh sách thuật ngữ cho phép, không đồng nhất có tiếng Anh với giọng điệu không đạt. |
| 6 | helpful HL-015 | PASS (FN) | FAIL | Người theo ledger được mô tả trong note | Reply nói 55.000đ, note ghi ledger 40.000đ. Tách tính đúng tiền sang code so reply–ledger; lịch sự không được bù sai tiền. |
| 7 | helpful HL-016 | PASS (FN) | FAIL | Người theo ledger được mô tả trong note | Reply xin lỗi dài nhưng nói 55.000đ thay vì ledger 35.000đ. Rubric không cộng điểm độ dài hoặc lời xin lỗi để bù lỗi nghiệp vụ; yêu cầu bằng chứng kết quả. |
| 8 | helpful HL-020 | PASS (FN) | FAIL | Người theo ledger được mô tả trong note | Reply nói 90.000đ, note ghi ledger 120.000đ. Kiểm cả nói cao hơn và thấp hơn ledger bằng code; không chỉ dò trường hợp phóng đại số tiền. |

Các kết luận về ledger ở bảng này dựa trên note trong CSV replay; chưa có ledger gốc của những hội thoại đó để kiểm chứng độc lập. Đây là audit bằng chứng công khai của học viên, không phải nhãn người mới hay một vòng đánh giá độc lập.

## Kết luận
- **Tone được dùng trong phạm vi giọng điệu:** đạt cả ba sàn, nhưng vẫn bỏ sót 6 lỗi và báo nhầm 4 case; không dùng kết quả này để chứng minh tiền/approval đúng.
- **Helpful bị loại khỏi gate:** ma trận TP=9, FP=0, FN=21, TN=70; recall 0.3 và κ 0.375 không đạt sàn. Ví dụ HL-016 cho thấy lời xin lỗi dài đi kèm sai tiền vẫn được PASS; vì vậy judge dễ thưởng phong cách và bỏ qua kết quả nghiệp vụ.
- **Tiền và approval phải kiểm bằng code.** Metric reply–ledger cho FM-08 sẽ triển khai ở M3; thay rubric mới chỉ là đề xuất, CSV replay chưa được chấm lại bởi judge mới.
- Không hạ FLOORS hoặc sửa nhãn CSV để hợp thức hóa helpful. Sau sửa rubric cần nhãn người độc lập, tập held-out mới và calibration lại.
- κ không xác định phải bị loại, không coi là đồng thuận hoàn hảo; Rogan–Gladen chỉ dùng khi sensitivity + specificity > 1 và cắt kết quả về [0, 1].
- Giới hạn: mỗi CSV chỉ có 100 dòng công khai, có nhiều mẫu câu lặp; judge replay không đo độ biến thiên của LLM thật, không có bằng chứng trên người dùng thật và chưa có held-out mới.
