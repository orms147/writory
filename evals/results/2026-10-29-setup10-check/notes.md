# Đo lại khởi tạo `setup-10` (D-122), so với `setup-9`

Người đọc: Claude và chủ dự án, 29/10/2026. Cùng cách đo với `../2026-10-29-setup9-check/notes.md`, nhưng chỉ năm đề x một seed (seed của đề), `bench_run --setup-only --budget 0.05`, một chuỗi nối tiếp. Model `openai/gpt-6-luna` (`reasoning: low`) cho vai `setup`; commit, hash config và model trong `meta.json` của năm thư mục `../2026-10-29-run-setup10-*`. Số liệu gộp ở `compare.json`. Mốc so: mười lượt `setup-9` của `../2026-10-29-setup9-check/`.

## Số đo
| | setup-9 (10 lượt, 54 nhân vật) | setup-10 (5 lượt, 26 nhân vật) |
|---|---|---|
| Mở bằng "Trông" | 54/54 | 0/26 |
| Mở trùng từ đầu (`opening_repeats`) | 44 | 3 |
| Màu tóc đầu tiên là "đen" | 43/54 | 2/26 |
| Trùng màu tóc trong cùng truyện (`hair_repeats`) | 34 | 6 |
| Lượt cần sửa D-54 | 3/10 | 2/5 (`milestones`; `edges` + `pacing`) |
| Khởi tạo hỏng | 0 | 0 |
| Độ dài `appearance` (ký tự) | 119–254, trung bình 171.5 | 149–253, trung bình 183.8 |
| Độ dài `visual` (ký tự) | 104–191, trung bình 141.1 | 110–168, trung bình 136 |
| Có `appearance` / `visual` | 54/54, 48/48 | 26/26, 23/23 |
| Chi phí khởi tạo trung bình mỗi lượt (USD) | 0.00473 | 0.00527 |
| Token ra của `build` đầu, trung bình | 4568 | 4905 |

Tổng chi của năm lượt: 0.0263 USD. Đề `build` dài thêm vài trăm token so với `setup-9` (ab-tu-tien: 4130 → 4334).

## Đọc được
- Cả hai điểm yếu đã đo ở `setup-9` mất: không văn bản nào mở bằng "Trông", gần như không còn mở trùng; tóc đen chỉ còn 2/26, và trong mỗi truyện hầu hết mọi người khác màu hoặc khác kiểu (hoa râm, nâu đỏ, bạc, vàng nâu, trắng...).
- Không còn thói quen hay cử chỉ: không văn bản nào có "luôn", "thường", "hay", "quen", "thói quen". Không ngoại hình nhân vật chính nào chép nghề hay quá khứ (đọc tay năm nhân vật chính: tả tuổi, mặt, vóc dáng, tóc, áo). Bộ `leak_terms` của kế hoạch không khớp văn bản nào.
- Lượt sửa D-54 hai trên năm vẫn là lỗi cũ (mốc, cạnh, nhịp), không do ngoại hình; 3/10 và 2/5 không phân biệt được với mẫu này.
- Chi phí khởi tạo tăng thêm khoảng 11% (0.00473 → 0.00527), trong đó có hai lượt sửa; token ra của `build` đầu tăng khoảng 7%.

## Mới lệch (đọc tay hai truyện đủ ngoại hình + năm nhân vật chính)
- **Khuôn câu giống nhau:** hầu hết ngoại hình có dạng "<mặt>, vóc người <...> và tuổi <...>. Tóc ..., áo ..., một <vật/dấu hiệu>". Từ mở đầu thay đổi (`Gương`, `Khuôn`, `Gò`, `Vóc`, `Mái`...) nhưng cấu trúc thì một: nhiều văn bản khác chữ mà cùng nhịp.
- **Màu tóc dồn sang nâu:** "nâu" thành màu đầu tiên ở 11/26 (thay cho "đen"); trùng màu vẫn có 6 trong cùng truyện.
- **Dấu hiệu nhận diện lặp giữa các truyện:** "vết sẹo mảnh chạy ngang cằm" (hoặc "vết sẹo ngắn dưới cằm") xuất hiện ở ba nhân vật thuộc ba truyện khác nhau (nhân vật chính ab-tu-tien, Vũ Đạt ở ab-ky-ao, nhân vật chính long-tu-tien). Trong cùng một truyện thì không trùng.
- Bộ đếm không bắt được hai điều này (nó chỉ đếm từ mở đầu và màu tóc).

## Chưa kiểm
- Mẫu nhỏ (5 lượt, 26 nhân vật; một seed). Khác biệt rất lớn ở "Trông" và "tóc đen" đủ rõ, nhưng tỉ lệ sửa D-54 và chi phí thì không.
- Chưa kiểm hai khuôn mặt "khác nhau" theo nghĩa hình ảnh khi đưa vào app video; chưa đo ảnh hưởng lên văn khi bật `limits.context.character_appearance_max_chars`.
- Cùng seed không cho cùng thế giới (model không tất định), nên so với `setup-9` chỉ ở mức tỉ lệ.
