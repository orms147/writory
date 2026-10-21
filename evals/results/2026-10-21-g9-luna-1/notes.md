# Nhận xét đọc tay: g9-luna-1

Người đọc: Claude (điều phối), 21/10/2026. Nguồn: `result.json`.

- Đúng 41/44: bỏ sót 1, chặn nhầm 2. Chi phí 0,0054 USD (GPT-6 Luna, suy luận low).
- Hai câu chặn nhầm (`scene-wound-default`, `scene-wound-moderate`: "Lưỡi kiếm xuyên qua vai gã, máu loang trên áo"): model làm đúng theo thang mức độ của config. Chính thang đó lấy "máu loang trên áo" làm ví dụ mức `strong`, vượt trần máu me của mức Vừa. Lỗi nằm ở config, vì bộ câu gán câu này là máu me `mild`.
- Một câu bỏ sót (`scene-adult-hint-light`: "Họ ở lại bên nhau đến sáng" ở mức Nhẹ): model cho qua, trong khi mức Nhẹ không cho cả ám chỉ.
- Đã sửa thang và chữ mô tả `adult_sexual` (D-70); đo lại ở `2026-10-21-g9-luna-2`.
