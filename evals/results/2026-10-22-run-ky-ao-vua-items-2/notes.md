# Nhận xét đọc tay: ky-ao-vua-items-2

Người đọc: Claude, 22/10/2026. Nguồn: `report.json`, `truth_dump.json`, `chapters/`.

- Lệnh: `bench_run --label ky-ao-vua-items-2 --scenario evals/scenarios/story_run/ky-ao-vua.yaml --chapters 10 --seed 20261021 --budget 0.13`, mã nhánh `feature/item-continuity` (D-90, chưa commit lúc chạy). Thế giới dựng khác lần 1 và khác `ky-ao-vua-3`, nên chỉ là chiều hướng, một lần chạy.
- 10/10 chương ghi; chi phí 0,0790 USD (`ky-ao-vua-3`: 0,0778). Viết lại 3; không cảnh bị chặn; `quality:repetition` ×3, không `leak:name`, không lỗi người canh.
- Lần chạy trước (`ky-ao-vua-items-1`) cùng code dừng ở chương 1 vì `leak:name`; lần này không gặp. Không phân biệt được là do thế giới hay do ngẫu nhiên.

## Đồ vật (từ `truth_dump.json`, đối chiếu `chapters/`)
- Ba đồ vật, chương 0 mỗi cái chỉ có một nơi, không cái nào có người giữ: không có đồ vật vừa giữ vừa ở nơi như trường hợp D-90 mô tả. **Lỗi chính D-90 (đồ thị tự mâu thuẫn) không xuất hiện trong thế giới này**, nên lần chạy không chứng minh luật mới sửa được nó; chứng minh là các test hồi quy trên dữ liệu của `ky-ao-vua-quotes-1`.
- `manh_ngoc_khac` ở `ruong_da` suốt 10 chương; văn ch05–ch10 đều tả nó "dưới phiến đá", khớp. Một chỗ lệch nhẹ: ch06:85 thuộc hạ "mang Mảnh Ngọc Khắc đến gần dây phong tỏa", ch07:5 lại "vẫn nằm dưới phiến đá": văn tả vật được mang ra xem rồi để lại, đồ thị không ghi chuyển.
- `lenh_di_doi` ở `doanh_trai_su_gia` tới ch08 rồi chuyển sang `ruong_da` (cạnh đóng và mở đúng ở ch08). Văn ch02:27 "Lệnh Di Dời vẫn nằm trong doanh trại" khớp; ch08:117 ông rút tờ lệnh tại phiên họp, khớp chỗ mới.
- `chuong_cu` ở `thap_bao_dong`, văn chỉ nhắc tiếng chuông, không mâu thuẫn.
- Cạnh bộ trích bỏ: 2 (`known_as` là tên nút khác ×1, sai schema ×1); không liên quan đồ vật.

## Chưa kiểm
- Lỗi lật trạng thái đồ vật (đồ vật vừa ở nơi vừa trong tay) chỉ kiểm bằng test, chưa thấy lại ở lần chạy thật nào sau D-90.
- Lỗi cửa mở/khoá: đồ thị không biểu diễn được, nên lần chạy này không đo.
- Mục "Đồ vật quan trọng" có làm `leak:name` ở `items-1` nhiều hơn không: cần lần chạy đối chứng cùng khởi tạo (`bench_run --setup-from` mới có ở nhánh `feature/page-quotes-writer`, chưa vào `main`).
