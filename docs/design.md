# WriTory — Tài liệu thiết kế

*Truyện tương tác tiếng Việt, nhớ mọi thứ bạn đã chọn.*

Ngày viết: 19/10/2026 · Tác giả ý tưởng: Nguyễn Hà Bách · Trạng thái: thiết kế bản 1; hiện trạng cài đặt ở `CLAUDE.md` mục 9.

Ký hiệu trong tài liệu:
- **[Chốt]** — người dùng (chủ dự án) đã nói rõ.
- **[Quyết định thiết kế]** — Claude đề xuất, chủ dự án đã đồng ý hướng chung nhưng chưa xét từng chi tiết; người làm được đổi nếu có lý do, ghi lại lý do.
- **[Để người làm quyết]** — không ảnh hưởng tới thứ được làm ra; chọn cách nào hợp lý cũng được.

---

## 1. Dự án này là gì và vì sao làm

Người dùng cùng AI viết một tiểu thuyết ngắn tới trung bình bằng cách sống cuộc đời nhân vật chính qua từng lựa chọn, giống cơ chế lựa chọn của game FMV nhưng bằng chữ. Hệ thống giữ một **trí nhớ thế giới dạng đồ thị** để truyện không quên ai, không quên chuyện gì, và không lộ bí mật trước thời điểm.

**Vì sao [Chốt]:**
- Mục đích học: học GraphRAG / bộ nhớ dạng đồ thị qua một dự án thật.
- Mục đích dùng: chủ dự án tự chơi, và có người dùng thật càng tốt.
- Vấn đề cần giải: truyện do AI viết **mất context** khi dài ra — quên nhân vật, quên quan hệ, viết ngược sự kiện cũ.

**Thành công là:**
1. Sau 30–60 chương, truyện vẫn nhớ đúng: ai còn sống, ai giữ gì, ai biết gì, quan hệ hiện tại.
2. Plot twist không bị lộ trước thời điểm.
3. Đo được bằng con số rằng đồ thị giúp (đúng hơn và/hoặc rẻ hơn) so với các cách không dùng đồ thị — hoặc ghi thật nếu không giúp.
4. Có người ngoài chơi hết một truyện và muốn chơi truyện thứ hai.

## 2. Mục tiêu, không làm, và thất bại

**Mục tiêu**
- Truyện tiếng Việt, độ dài người dùng chọn, tối đa khoảng 100 trang Word. [Chốt]
- Lựa chọn nhiều kiểu: hành động, lời thoại, nội tâm. [Chốt]
- Giữ bí mật: người chơi chỉ biết những gì góc nhìn của họ được biết. [Chốt]
- Đồ thị là trung tâm của kiến trúc, và có bộ đo chứng minh giá trị của nó.

**Không làm** [Quyết định thiết kế]
- Ảnh, video, giọng đọc. Chỉ lấy cơ chế lựa chọn của FMV, không làm FMV thật.
- Nhiều người chơi chung một truyện.
- Tiểu thuyết dài hàng trăm chương (trên 100 trang).
- Ứng dụng di động riêng. Chỉ web, hiển thị được trên điện thoại.
- Tự huấn luyện model viết truyện.

**Thất bại dù vẫn chạy được**
- Truyện vẫn mâu thuẫn sau 20 lựa chọn.
- Lộ twist: sổ tay, câu trả lời của người kể, hay một lựa chọn bị khoá để lộ điều người chơi chưa được biết.
- Đồ thị đúng nhưng văn khô như biên bản.
- Chi phí mỗi truyện quá cao để cho người khác dùng.
- Người dùng tự viết hành động phá được luật thế giới ("tôi trở thành thần") mà truyện vẫn chiều theo.

## 3. Độ dài truyện [Chốt: nhiều mức, tối đa ~100 trang]

Quy đổi: 1 trang Word A4, chữ 12–13, giãn dòng đơn ≈ 3.000 ký tự. Một chương dài 3.000–10.000 ký tự (≈ 1–3,5 trang).

| Mức | Khoảng trang | Ký tự | Số chương |
|---|---|---|---|
| Truyện ngắn | ~10 | ~30.000 | 4–8 |
| Truyện vừa | ~30 | ~90.000 | 10–20 |
| Truyện dài | ~60 | ~180.000 | 20–35 |
| Tiểu thuyết mỏng | ~100 | ~300.000 | 30–60 |

Mức độ dài quyết định nhịp truyện (xem §6.1): khi nào mở mạch, khi nào lộ twist, khi nào cao trào và kết. Truyện ngắn phải có kết tử tế, không cắt ngang.

Bản 1 người chơi chỉ chọn được Truyện ngắn và Truyện vừa. Truyện dài và Tiểu thuyết mỏng mở sau khi đã chạy đo thật ở mức đó; lệnh đo vẫn chạy được mọi mức. Mức nào mở: `config/story_lengths.yaml`, `player_selectable` (D-88).

Lưu ý: 300.000 ký tự tiếng Việt ước khoảng 100.000 token (chưa đo, tuỳ tokenizer). Một số model nhét vừa cả truyện vào prompt, nên "nhét cả truyện" là một đối thủ bắt buộc trong bộ đo (§9).

## 4. Người dùng trải qua gì

### 4.1 Khởi tạo (~2 phút)
1. Chọn tag: một thể loại chính (ví dụ tu tiên, trinh thám, đô thị, hậu tận thế; thể loại đã gồm thời đại), tag phụ tuỳ chọn, giọng văn (D-65). Mức độ u tối là một trong các mức có sẵn (`config/moderation.yaml`, `darkness_levels`), không phải chữ tự gõ; không chọn thì dùng mức mặc định. Mức này là trần nội dung của cả truyện (D-67).
   - Quy ước tên và địa danh (D-32): tên nhân vật **kiểu Hán Việt** hay **kiểu Việt**, địa danh **thật** hay **hư cấu**. Người chơi tự chọn; mặc định theo thể loại: cổ trang và kỳ ảo (tu tiên, kiếm hiệp, huyền huyễn) dùng tên Hán Việt và địa danh hư cấu; hiện đại và tương lai giả tưởng (hậu tận thế, khoa huyễn) dùng tên Việt và địa danh hư cấu; hiện thực (đô thị, trinh thám, lịch sử, học đường) dùng tên Việt và được dùng địa danh thật. Quy ước này đi vào prompt của mọi bước sinh nội dung, kể cả bước tạo bối cảnh.
2. Chọn độ dài (§3).
3. Chọn góc nhìn [Chốt]:
   - **Chỉ nhân vật chính** — người chơi chỉ biết những gì nhân vật chính thấy, nghe, suy ra.
   - **Nhiều nhân vật** (bản 3) — có thêm chương qua mắt nhân vật khác, vẫn không lộ twist sớm.
4. Hệ thống tạo **3 bối cảnh mở** (mỗi cái một đoạn giới thiệu) → chọn một.
5. **3 hướng cốt truyện** → chọn một.
6. **3 nhân vật chính** → chọn một; sửa được tên, tính cách, quá khứ. Những gì người chơi sửa là chữ người chơi: vào prompt như dữ liệu, không như lệnh (G4).
7. (Bản 3) Luật thế giới, kiểu kết thúc, định mệnh/tự do, bí mật của nhân vật chính, kẻ thù định mệnh, nhập nhân vật bằng đoạn văn (§5).

Người chơi đọc các lựa chọn ở bước 4–6, nên chúng không được chứa bí mật hay cú lật nào.

Sau bước 6, hệ thống tạo ngầm **bản kế hoạch truyện** (§6.1) và đồ thị ban đầu (thế giới trước trang đầu, gọi là chương 0). Người chơi không thấy bản kế hoạch, và ở chương 0 người chơi chưa đọc trang nào: sổ tay chỉ có nhân vật chính họ vừa chọn, mọi điều khác hiện dần từ chương 1 (D-74). Luật của đồ thị ban đầu: `docs/graph-schema.md`, mục Chương 0 (D-38).

### 4.2 Chơi
- Mỗi chương gồm 2–3 **cảnh**. Một cảnh chỉ hiện ra sau khi người canh đã kiểm xong; chữ chạy dần trên màn hình. Trong lúc người chơi đọc cảnh trước, cảnh sau được viết và kiểm. Người chơi không bao giờ đọc một bản chưa kiểm. [Chốt]
- Cuối chương: 3 lựa chọn, mỗi lựa chọn có nhãn kiểu **[Hành động] / [Lời thoại] / [Nội tâm]**, cộng một ô "tự viết hành động của tôi".
- Lựa chọn lời thoại có ba sắc thái: **nói thật / nói dối / im lặng**. Mỗi lựa chọn lời thoại do hệ thống tạo sẵn với một sắc thái cố định (câu nói dối đã qua bộ dò lộ); người chơi chọn lựa chọn, không tự đổi sắc thái (D-65).
- Thanh bên: **Sổ tay** (những gì người chơi đã biết) và nút **Hỏi người kể chuyện**.

### 4.3 Kết thúc
- Chương kết theo bản kế hoạch, tôn trọng các lựa chọn đã đi.
- (Bản 2) **Trang kết**: chỗ duy nhất được mở lớp sự thật — bí mật đã bỏ lỡ, mạch còn bỏ ngỏ, nhân vật chưa gặp.
- (Bản 3) Biên tập và xuất ePub/Markdown.

## 5. Danh sách tính năng theo bản

**Bản 1 — chơi được với bạn bè (6 tuần)** [Quyết định thiết kế]
| Tính năng | Ghi chú |
|---|---|
| Khởi tạo: tag, độ dài, góc nhìn chỉ nhân vật chính, 3 bối cảnh / 3 hướng / 3 nhân vật | độ dài chỉ Ngắn và Vừa (§3, D-88) |
| Chương hiện theo từng cảnh đã kiểm, 3 lựa chọn ba kiểu + ô tự viết | |
| Người chơi dùng key OpenRouter của chính mình (§10) | |
| Lớp chất lượng: chọn mức model, tách vai, dàn ý trước, kiểm văn bằng code (§6.5) | chưa có lượt biên tập |
| Đồ thị hai lớp (§7) | lõi |
| Người canh: mâu thuẫn + lộ sớm, viết lại tối đa 1 lần (§8) | lõi; chỉ kiểm bằng code, phần LLM để bản sau (D-88) |
| Sổ tay (chỉ lớp người chơi biết) | chỉ xem |
| Hỏi người kể chuyện (chỉ trả lời từ lớp người chơi biết) | không mất lượt |
| Đăng nhập đơn giản, lưu truyện, mở lại chơi tiếp | đăng nhập bằng mã mời cho bạn bè (D-89) |
| Bộ đo (§9) | lõi |

**Bản 2 — chiều sâu (+4 tuần)**
- Lựa chọn bị khoá theo những gì người chơi biết (chỉ hiện khi đã mở, **không hiện ô xám**).
- Theo dõi cài cắm: chi tiết được gieo thành mạch "chưa gỡ"; truyện phải thu hoạch.
- Người đọc **ghim chi tiết** → thành cài cắm.
- Nhảy thời gian (tua 1 tháng / 3 năm, cập nhật đồ thị: già đi, chết, quan hệ phai).
- Trang kết.
- Cây đời: quay lại một ngã rẽ cũ, đi nhánh khác.
- Chỉnh nhịp: "chậm lại, tả kỹ" / "nhanh lên".

**Bản 3 — hoàn thiện (+4 tuần)**
- Chế độ nhiều góc nhìn (chương nhân vật phụ chỉ biết đúng những gì họ biết).
- Luật thế giới (người canh chặn cảnh vi phạm).
- Định mệnh/tự do; kiểu kết mong muốn.
- Bí mật của nhân vật chính; kẻ thù định mệnh và người đồng hành.
- Nhập nhân vật bằng đoạn văn (trích đồ thị từ văn bản).
- **Nhập tài liệu nguồn** (bài báo, file `.md`/`.txt`, ghi chép thế giới tự viết) để dựng cốt truyện theo đó [Chủ dự án đề xuất, xếp vào bản 3]. Đây là phần GraphRAG "cổ điển": trích thực thể/quan hệ từ văn bản có sẵn thành đồ thị nền, rồi mới tạo 3 bối cảnh từ đó.
  - Hai chế độ: **lấy cảm hứng** (chỉ mượn chủ đề, bối cảnh, xung đột) và **bám sát** (sự thật trong tài liệu thành ràng buộc, người canh kiểm như `Rule`).
  - Nội dung tài liệu là chuyện người chơi đã đọc, nhưng nhân vật chính chưa chắc đã biết. Bí mật và twist phải là phần **mới** do bản kế hoạch tạo ra, không lấy từ tài liệu, nếu không thì chẳng còn gì bất ngờ.
  - Tài liệu là chữ người chơi đưa vào: bọc như dữ liệu (G4), có trần độ dài, và báo trước chi phí trích (tính trên key người chơi).
  - **Người thật** trong bài báo: mặc định đổi sang nhân vật hư cấu, và cảnh báo người chơi (xem §13).
- Sửa sự thật ("Không, Lan chưa biết chuyện đó").
- "Nếu như…": tóm tắt nhánh không chọn, chỉ trong phạm vi nhân vật chính có thể biết.
- Biên tập trước khi xuất, xuất ePub.
- **Xuất kịch bản để làm video AI** [Chủ dự án đề xuất 28/10/2026, xếp vào bản 3, D-107]: từ truyện đã chơi xuất kịch bản hoàn chỉnh (cảnh theo thứ tự, nơi chốn, ai có mặt, lời thoại tách theo người nói, nhịp hành động), bảng nhân vật có mô tả ngoại hình cố định, và sơ đồ tuyến nhân vật theo chương (quan hệ, điều biết, sự kiện; dựng từ đồ thị), để gửi sang app tạo video như Seedance. Lựa chọn của chủ dự án (D-118): nguồn là toàn bộ `truth`; đầu ra là danh sách shot kèm prompt tiếng Anh, lời thoại theo ngôn ngữ người xuất chọn; ngoại hình sinh lúc khởi tạo và cố định. Phần nền làm sớm, sau đợt truyện dài. Đã làm sớm theo D-125 dưới dạng lệnh của admin (`python -m writory.export.video`), KHÔNG có trong app: chỉ ai cầm DB mới xuất được.
  - Phần lớn đã có trong đồ thị và dàn ý cảnh. Ngoại hình nhân vật và cảnh sắc nơi chốn đã được sinh lúc khởi tạo (D-120, D-122); thời điểm của cảnh (ngày, đêm) chưa có trong dàn ý, bộ xuất cho model đoán từ chữ của cảnh.
  - Nguồn là toàn bộ `truth`, kể cả bí mật chưa lộ (D-118), nên bản xuất không bao giờ tới người chơi: chỉ admin cầm DB chạy được, không có đường từ API hay giao diện (D-125).

**Để sau bản 3:** chia sẻ thế giới cho người khác chơi với nhân vật khác.

## 6. Cách truyện được viết

### 6.1 Bản kế hoạch truyện (ẩn) [Quyết định thiết kế]
Tạo lúc khởi tạo, cập nhật khi lựa chọn làm lệch hướng:
- Các hồi (mở đầu, phát triển, cao trào, kết) quy ra số chương theo mức độ dài: các hồi phủ liền từ chương 1, tổng số chương nằm trong khoảng của mức đã chọn (§3).
- Các **mốc** chính của cốt truyện (bước ngoặt, cao trào, kết), mỗi mốc có khoảng chương và một câu mục tiêu. Mỗi hồi có ít nhất một mốc; mốc kết nằm ở chương cuối. Số mốc theo mức độ dài (`config/story_lengths.yaml`).
- Vài bí mật lớn (số lượng cho phép: `SECRETS_MIN`, `SECRETS_MAX` trong `backend/src/writory/pipeline/setup.py`), mỗi cái là một sự thật có trong đồ thị ban đầu, kèm **khoảng chương dự kiến lộ** (ví dụ "Lan là gián điệp: lộ trong chương 12–16") và các cụm từ để bộ dò lộ nhận ra khi bí mật bị nói ra sớm (D-26). Bí mật về danh tính kèm các nút có tên phải giữ kín tên tới khi lộ (D-61).
- Các mạch chính và phụ; mạch phải gỡ trước khi kết mang **khoảng chương phải gỡ**.
- **Nhịp** định trước từ đầu, dày hay thưa theo độ dài truyện: mỗi chương có tối đa một số việc đến hạn (bí mật, mạch phải gỡ, mốc), số trong `config/story_lengths.yaml`, để hạn không dồn vào một chương. Chương cuối không tính, vì chương kết gỡ nhiều mạch cùng lúc (D-54). Mọi khoảng nằm trong số chương của truyện. Kiểm bằng code lúc khởi tạo (D-49).

Bản kế hoạch là nguồn để người canh biết thế nào là "lộ sớm" và "trễ hạn", và là nguồn của mục tiêu mỗi chương (§6.2 bước 1). Lựa chọn của người chơi được phép kéo sớm hoặc lùi một lần lộ (ví dụ người chơi chủ động điều tra Lan), nhưng việc đó phải xảy ra qua một cảnh hợp lý, không tự nhiên lộ ra.

### 6.2 Đường đi của một chương
Một chương = 2–3 cảnh. Mỗi cảnh đi qua:
```
lấy phần đồ thị liên quan  →  viết cảnh  →  trích thay đổi  →  kiểm tra  →  (sai? viết lại 1 lần)  →  hiện cho người chơi
```
Hết cảnh cuối: **ghi thay đổi của cả chương vào đồ thị** → **tóm tắt chương** → **tạo 3 lựa chọn**. Tóm tắt do vai `summary` viết từ chữ đã hiện của chương (ngôi thứ ba, luôn gọi nhân vật chính bằng tên chuẩn trong đồ thị, D-112), lưu ở Postgres, chỉ vào đề của các chương sau; lỗi khi tóm tắt không làm hỏng chương đã ghi, chương sau chạy thiếu tóm tắt đó (D-49). Chương cuối của bản kế hoạch thì không tóm tắt, không tạo lựa chọn: truyện kết, giao diện nhận sự kiện `story_finished` (D-50).

1. **Lấy phần đồ thị liên quan:** nhân vật có mặt và hàng xóm 1–2 bước của họ, địa điểm, đồ vật đang giữ, quan hệ hiện tại, bí mật người có mặt biết, lời nói dối đang "treo", mạch đang mở, mục tiêu của chương theo bản kế hoạch, tóm tắt 2 chương gần nhất (chương 1 không có; bọc như dữ liệu vì viết từ văn có chữ người chơi), lựa chọn hay hành động dẫn tới chương, vài đoạn nguyên văn đã hiện trên trang ở các chương đã ghi (tắt mặc định, chưa đo ra lợi; chọn bằng BM25 theo nhân vật, đồ vật, nơi chốn của cảnh và lựa chọn vừa rồi; bọc như dữ liệu; chỉ vào đề dàn ý và đề viết; D-85), và các cảnh đã viết của chương này (kèm thay đổi đã trích, chưa ghi). Mục tiêu của chương (D-49) gồm hồi và vị trí trong hồi, mốc của chương và mốc kế tiếp, bí mật đã tới khoảng lộ (bí mật nào đến hạn), mạch phải gỡ và hạn gỡ, và chương này có phải chương cuối không; chỉ vào đề dàn ý và đề viết (riêng mạch phải gỡ và hạn gỡ cũng vào đề bộ trích ở bước 3, D-82). Ở chương cuối, đề đòi kết truyện: gỡ các mạch còn mở, lộ các bí mật còn lại nếu hợp lý, cảnh cuối không bỏ lửng.
2. **Viết cảnh** với model viết văn; tổng độ dài chương theo mức đã chọn.
3. **Trích thay đổi** từ cảnh vừa viết, dạng JSON có cấu trúc: thực thể mới, quan hệ đổi, ai biết thêm điều gì, đồ vật đổi chủ, ai chết, lời hứa/món nợ mới, điều gì vừa được hé lộ cho người chơi. Extractor chỉ được tham chiếu id thực thể có sẵn trong danh sách được đưa vào. Ngoại lệ duy nhất: `Fact` mới từ trang (`new_facts`), kèm câu trích nguyên văn, code kiểm và sinh id, đã hé lộ cho người chơi, có trần mỗi chương (D-93).
4. **Kiểm tra** (§8). Nếu sai: viết lại cảnh một lần kèm danh sách lỗi. Nếu vẫn sai: giữ bản thứ hai, ghi lỗi vào nhật ký để đo, không chặn người chơi. Nếu bản đầu chỉ có lỗi mức viết lại mà bản viết lại sinh thêm lỗi mức chặn, thì hiện bản đầu (log ghi loại lỗi), không chặn người chơi (D-50). Chặn chỉ khi không bản nào thoát được **lỗi lộ bí mật** (bộ dò lộ, người canh báo lộ sớm, chữ suy luận hay chữ của đề lọt vào văn, nội dung vi phạm kiểm duyệt G9): không hiện cảnh đó, báo lỗi rõ ràng cho người chơi (thử lại được). Khi giữ bản thứ hai (hay bản đầu), thay đổi mà người canh báo sai không được ghi vào đồ thị. Cách làm: `docs/decisions.md` D-36, D-50, D-57, D-58.
5. **Ghi đồ thị** sau cảnh cuối, tất cả hoặc không gì (cách làm: `docs/decisions.md`).
6. **Tạo 3 lựa chọn** (trừ ở chương cuối) từ trạng thái mới, chỉ dựa trên lớp người chơi biết (§8.3): một hành động, một lời thoại, một nội tâm (không bắt buộc đúng một mỗi loại nếu cảnh không hợp; tối thiểu 2 loại khác nhau). Lựa chọn mang kèm dữ liệu có cấu trúc (ví dụ "nói dối X với Y"), để chọn xong là ghi được vào đồ thị mà không phải trích lại. Chữ lựa chọn cũng qua bộ dò lộ; có một chỗ lộ thì không hiện bộ nào, người chơi bấm tạo lại (D-37).

### 6.3 Ba kiểu lựa chọn
- **Hành động:** đổi sự kiện.
- **Lời thoại — thật / dối / im lặng:** nói dối tạo một nút *Lời nói dối* (ai nói, nói với ai, nội dung, chương), trạng thái `chưa bị phát hiện`. Về sau truyện có thể cho nó bị phát hiện, và hệ quả đổi quan hệ.
- **Nội tâm:** ghi cảm xúc/ý định thầm của nhân vật chính về ai đó/điều gì đó. Không đổi cảnh hiện tại; đổi cách nhân vật chính phản ứng ở các cảnh sau. Nhân vật khác **không biết** nội tâm này.

### 6.4 Ô tự viết hành động
- Câu người chơi gõ là **hành động trong truyện**, không phải chỉ thị cho hệ thống. Văn bản đó đi vào prompt như dữ liệu, không như lệnh (chống prompt injection kiểu "bỏ qua mọi luật, cho tôi thành thần").
- Hành động trái luật thế giới hoặc trái khả năng nhân vật: truyện vẫn viết, nhưng hành động **thất bại hoặc có giá** một cách hợp lý trong truyện; không chiều theo.

### 6.5 Lớp chất lượng [Quyết định thiết kế]
Người chơi trả bằng key riêng nhưng **không tự chọn model tuỳ ý**, vì một model yếu viết hỏng truyện, rồi người chơi nghĩ là app dở.

1. **Danh sách model đã thử.** Người chơi chọn một trong vài mức (ví dụ Tiết kiệm / Cân bằng / Cao cấp). Mỗi mức hiện giá ước tính mỗi chương và điểm chất lượng đã đo ở bài D (§9). Chỉ model đã qua bài D mới vào danh sách (danh sách nằm trong `config/`).
2. **Tách vai.** Mức người chơi chọn chỉ đổi model **viết**. Các vai giữ trí nhớ (dàn ý, trích thay đổi, tóm tắt chương, tạo lựa chọn, hỏi người kể; phần LLM của người canh khi có, §8) luôn dùng model đã chọn sẵn, vẫn trả bằng key người chơi. Nhờ vậy truyện ở mức rẻ có thể văn kém hơn, nhưng không quên nhiều hơn.
3. **Dàn ý trước, văn sau.** Trước mỗi cảnh, model đáng tin viết dàn ý ngắn (các nhịp: chuyện gì xảy ra, ai nói gì, kết cảnh ở đâu). Model viết chỉ mở rộng dàn ý thành văn. Model yếu viết tốt hơn hẳn khi có nhịp rõ. Dàn ý viết tiếng Việt; dàn ý lẫn chữ khác hệ coi như sai schema và được thử lại (D-51).
4. **Hướng dẫn văn phong tiếng Việt** dùng chung cho mọi model: xưng hô đúng quan hệ, tránh văn dịch, tránh sáo ngữ hay gặp ở văn AI, nhịp câu theo giọng văn đã chọn, kèm vài đoạn mẫu. Lời thoại theo kiểu gạch đầu dòng (D-18): mỗi lượt một dòng, mở bằng "- "; backend chuẩn hoá mọi "—"/"–" thành "-" trước khi kiểm và trước khi hiện (D-31). Bản hiện hành (v3, D-111): `evals/scenarios/quality/style_guide_vi.md`.
5. **Kiểm chất lượng bằng code** trên mỗi cảnh, không tốn lời gọi model (ngưỡng và danh sách sáo ngữ: `config/quality.yaml`, D-19):
   - độ dài nằm trong khoảng;
   - tỉ lệ lặp cụm từ (tên và biệt danh thực thể tính như một từ, D-51);
   - danh sách sáo ngữ cấm;
   - **lẫn chữ khác hệ** (chữ Hán, chữ Latin không dấu dài), một lỗi hay gặp ở một số model;
   - định dạng lời thoại;
   - **ngôi kể**: lời kể (không tính lời thoại) đúng ngôi đã chốt của truyện (`config/quality.yaml`, D-51). Đề của model viết nói ngôi này, lấy từ cùng giá trị.

   Hỏng thì viết lại một lần, chung lượt viết lại với người canh.
6. (Bản 3) **Lượt biên tập** tuỳ chọn: một model tốt đọc lại cảnh, sửa câu chữ, không đổi sự kiện. Lượt này tốn thêm tiền, nên người chơi tự bật.

### 6.6 Hỏi người kể chuyện
- Câu hỏi về thế giới, không mất lượt.
- Chỉ trả lời từ **lớp người chơi biết** (§7). Câu chưa được hé lộ → "Bạn chưa biết điều này." Không gợi ý, không úp mở về sự tồn tại của bí mật: sổ tay không trả lời thẳng được câu hỏi (có phải không, ai làm, nội dung gì, vì sao) thì cũng là câu đó, không kể mục lân cận thay vào. Câu trả lời nói về việc thiếu thông tin ("chưa có nội dung được ghi lại") bị code đổi thành câu đó (D-78).
- Người chơi gọi một người, nơi hay vật bằng chữ khác sổ tay thì người kể vẫn nhận ra. Câu hỏi chỉ biết được một phần thì người kể nói phần đã biết, không đoán phần còn lại (D-77).
- Câu trả lời kèm số câu hỏi còn lại của chương và nguồn: các chương mà người chơi đã biết những mục sổ tay câu trả lời dựa vào (D-65).
- Số câu hỏi mỗi chương có trần (`config/limits.yaml`, G8). Hết lượt thì báo bằng câu trung tính; sang chương sau thì có lượt mới.

## 7. Đồ thị thế giới

### 7.1 Hai lớp [Chốt ý, chi tiết là Quyết định thiết kế]
1. **Lớp sự thật:** đầy đủ, chỉ AI viết truyện và người canh thấy.
2. **Lớp người chơi biết:** những điều đã được hé lộ **trên trang truyện**, kèm chương hé lộ.

Không làm hai đồ thị riêng. Cùng một đồ thị; mỗi sự thật có thông tin "ai biết, từ chương nào". Người chơi (góc nhìn chỉ nhân vật chính) được coi là biết đúng những gì **nhân vật chính** biết, cộng những gì người kể đã mô tả trực tiếp trên trang trong phạm vi góc nhìn đó.

### 7.2 Mô hình [Quyết định thiết kế, người làm được chỉnh]
**Nút**
- `Character` (tên, biệt danh, tính cách, còn sống, …)
- `Location`, `Item`, `Faction`
- `Event` (chương, mô tả ngắn)
- `Fact` — một mệnh đề có thể là bí mật ("Lan là gián điệp của Hội Kiếm")
- `Lie` — lời nói dối (người nói, người nghe, nội dung, đã bị phát hiện chưa)
- `Thread` — mạch/cài cắm (mô tả, trạng thái mở/đã gỡ, chương gieo, khoảng chương dự kiến gỡ)
- `Rule` — luật thế giới (bản 3)
- `Chapter`, `Choice`, `Branch`

**Cạnh (ví dụ)**
- `RELATES_TO` (kiểu: bạn/thù/yêu/thầy trò…, mức −100…100)
- `LOCATED_AT`, `HOLDS`, `MEMBER_OF`, `PARTICIPATED_IN`
- `KNOWS` (Character → Fact/Lie/Event; `since_chapter`, `how`: chứng kiến/được kể/suy ra)
- `FEELS` (chỉ nhân vật chính, từ lựa chọn nội tâm)
- `TOLD` (Character → Lie → Character)
- `REVEALED_TO_PLAYER` (Fact/Event → Chapter)

**Thời gian:** mọi cạnh có `valid_from_chapter` và `valid_to_chapter` (rỗng = còn hiệu lực). Không xoá sự thật cũ; đóng nó lại. Hỏi "ở chương 8 B là gì của A" trả lời được.

**Nhánh (bản 2):** rẽ nhánh = **sao chép** đồ thị của truyện tại chương rẽ sang một đồ thị mới (nút mang `story_id` mới). Đồ thị một truyện nhỏ (cỡ vài nghìn nút), nên sao chép rẻ, và mọi truy vấn vẫn đơn giản như truyện một nhánh. Bản 1 không cần chuẩn bị gì cho nhánh ngoài việc mọi nút/cạnh đã mang `story_id`. Lý do: `docs/decisions.md`.

**Phân tách người dùng:** mọi nút/cạnh mang `story_id`; mọi truy vấn đi qua một lớp truy cập bắt buộc lọc theo `story_id`.

### 7.3 Ví dụ truy vấn phải trả lời được
- Ai đang giữ thanh kiếm ở chương hiện tại?
- Minh có biết Lan là gián điệp không, từ chương nào, biết bằng cách nào?
- Người chơi đã được biết điều gì về Lan?
- Những lời nói dối nào của nhân vật chính chưa bị phát hiện, đã nói với ai?
- Mạch nào đang mở và đã quá khoảng chương dự kiến gỡ?

## 8. Người canh

Chạy sau mỗi chương, trên kết quả trích thay đổi và văn bản chương:
1. **Mâu thuẫn:** người đã chết xuất hiện/hành động; đồ vật ở hai nơi; nhân vật biết điều họ chưa biết (đối chiếu `KNOWS`); quan hệ đổi đột ngột không có sự kiện giải thích; vi phạm `Rule` (bản 3).
2. **Lộ sớm:** chương hé lộ cho người chơi một `Fact` mà bản kế hoạch chưa tới khoảng lộ, và không có lựa chọn/cảnh nào của người chơi dẫn tới việc đó.
3. **Lộ qua giao diện:** sổ tay, câu trả lời của người kể, văn bản lựa chọn không được chứa điều thuộc lớp sự thật mà người chơi chưa biết. Kiểm bằng code (lọc theo `REVEALED_TO_PLAYER`/`KNOWS` của nhân vật chính), không chỉ nhờ LLM. Chỉ cảnh mới được hé lộ: trên người kể và lựa chọn, bộ dò lộ chặn mọi bí mật chưa có trong lớp người chơi biết, kể cả khi đã tới khoảng lộ (D-61).
4. **Trễ hạn:** hết chương mà bí mật đã tới chương cuối của khoảng lộ vẫn chưa lộ, hoặc mạch phải gỡ đã tới hạn vẫn chưa gỡ (ở chương cuối thì mọi bí mật và mạch phải gỡ đều đến hạn). Chỉ kiểm ở cảnh cuối chương, mức viết lại: model không lộ kịp thì truyện vẫn đi tiếp, không chặn người chơi (D-49).

Kiểm tra gồm phần quy tắc bằng code (truy vấn đồ thị) và phần LLM (đọc văn bản tìm điểm nghi). Phần nào kiểm được bằng code thì phải kiểm bằng code. Phần code kiểm gói thay đổi của từng cảnh trước khi ghi (D-23).

**Bản 1 chỉ có phần code** (D-88). Người canh chỉ thấy điều bộ trích đã ghi vào gói thay đổi: điều văn viết ra mà bộ trích không ghi thì không bị kiểm, và hành động vượt luật được chiều theo (G6) chưa có ai kiểm. Phần LLM để bản sau, khi đã có bài B cho nó; config chưa có vai model cho người canh.

Khi có phần LLM, mọi điểm nghi do LLM báo phải kèm **câu trích nguyên văn** từ cảnh; code kiểm câu trích có thật trong văn bản, không có thì bỏ điểm nghi đó. Việc đánh dấu một bí mật là "đã hé lộ cho người chơi" cũng phải kèm câu trích, vì đánh dấu sai sẽ làm sổ tay lộ bí mật. Chi tiết guardrail: `docs/security.md`.

## 9. Bộ đo

Các bài đo tách riêng, để biết lỗi nằm ở bộ nhớ, ở người canh, ở bước trích, ở model viết hay ở người kể:

**A. Bộ nhớ (QA trên truyện cố định).** Mọi đối thủ đọc **cùng một bộ chương đã viết sẵn** rồi trả lời cùng bộ câu hỏi. Không dùng kịch bản lựa chọn ghi sẵn để sinh lại truyện, vì mỗi hệ thống sẽ viết ra truyện khác nhau và câu hỏi không còn khớp. Câu hỏi chia nhóm (đồ vật, sống/chết, ai biết gì, quan hệ hiện tại, lời nói dối), và chia theo **khoảng cách**: sự thật gieo ở đầu, giữa hay cuối truyện, hỏi ở chương cách đó bao xa. Lỗi của truyện dài hay dồn ở phần giữa. Đáp án lấy từ đồ thị đã được **người kiểm tay**, không lấy từ chính hệ thống được đo.

**B. Người canh (lỗi cài sẵn).** Lấy các cảnh sạch, cài vào lỗi đã biết (người chết hành động, đồ vật ở hai nơi, nhân vật biết điều chưa biết, lộ twist sớm). Đo người canh bắt được bao nhiêu (recall), và báo nhầm bao nhiêu trên cảnh sạch.

**C. Trích thực thể.** Bộ câu tiếng Việt khó: trùng họ ("Nguyễn"), biệt danh, đổi tên, đại từ xưng hô đổi theo quan hệ (anh/em → mày/tao). Đo gộp/tách thực thể đúng bao nhiêu.

**D. Chất lượng văn theo model.** Mọi model ứng viên viết cùng một bộ dàn ý cảnh khai trước, đủ nhiều đề vì độ biến thiên giữa các đề lớn hơn giữa các lần sinh. Giám khảo LLM chấm tuyệt đối theo thang khai trước (tiếng Việt tự nhiên, xưng hô, bám dàn ý, giữ bí mật, …), mỗi tiêu chí kèm câu trích. Chủ dự án chấm tay một mẫu cảnh để đo mức đồng thuận với giám khảo. Kết quả quyết định danh sách model ở §6.5. Chạy lại khi thêm model mới. Cách chấm: D-25; lệnh: `docs/eval.md`.

**E. Hỏi người kể không lộ.** Bộ câu hỏi khai trước trên truyện cố định, theo từng chương: hỏi điều đã mở khoá, hỏi thẳng bí mật chưa mở, hỏi vòng hay bắt đoán, nhập vai hay chèn lệnh, hỏi meta, hỏi tên thật của người chỉ được biết qua biệt danh. Ghi riêng câu trả lời thô của model và câu người chơi thấy, để biết model tự giữ được bao nhiêu và lớp code (§6.6, §8 mục 3) phải chặn bao nhiêu. Chấm bằng code với chuỗi cấm chặt hơn lớp chặn đang đo; lộ ở câu người chơi thấy phải bằng 0. Đo cả tỉ lệ trả lời được câu đã mở khoá, để biết người kể có bị chặn oan không. Giám khảo LLM (tuỳ chọn) chỉ đọc câu người chơi thấy cùng sổ tay, không thấy lớp sự thật. Cách làm: D-53; lệnh: `docs/eval.md`.

**F. So model viết trên cùng một thế giới.** Các model viết chạy hết đường viết trên cùng một khởi tạo, cùng seed, vài chương. Giám khảo LLM chấm mù cả truyện (liền mạch, nhịp, lựa chọn), so trực tiếp với hai thứ tự trình bày, rồi mới thấy chi phí thật để khuyến nghị model đáng tiền. Khác bài D ở chỗ chấm truyện nhiều chương và có chi phí thật của cả đường chạy. Cách làm: D-101, giám khảo thứ hai D-108; lệnh: `docs/eval.md`.

**Đối thủ cho bài A:**
1. Không bộ nhớ (chỉ chương trước).
2. Tóm tắt cuộn (rolling summary).
3. RAG vector thường trên các chương cũ.
4. Nhét cả truyện vào prompt (khi vừa context).
5. Đồ thị (dự án này).

Bản 1 đã chạy cả năm đối thủ của bài A (đối thủ 3 là RAG BM25, chưa phải RAG vector, D-73; lần đầu: `evals/results/2026-10-21-memory-lan-1/`), bài B (chỉ phần kiểm bằng code, D-88), bài C v1 để chọn model trích (D-34, D-35), bài D (để chọn model), bài E và bài F. Bài C đầy đủ (thực thể mới, gộp hay tách biệt danh, trùng họ) để bản 2.

**LLM làm giám khảo** (khi cần): khác họ model với model viết, chấm nhiều lần và chấm thêm khi các lần lệch nhau (số lần của bài D: D-25), bắt trích nguyên văn, và có một mẫu do người chấm để báo mức đồng thuận.

**Chỉ số**
- Độ đúng trên bộ câu kiểm (kèm số mẫu `n` và khoảng tin cậy).
- Tỉ lệ chương có mâu thuẫn (người chấm + người canh).
- Tỉ lệ lộ sớm.
- Chi phí mỗi chương và mỗi truyện; token vào/ra.
- Thời gian chờ tới chữ đầu tiên và tới hết chương.

**Nguyên tắc:** khai trước câu hỏi và cách chấm rồi mới chạy. Đồ thị không thắng thì ghi thật là không thắng.

## 10. Chi phí
- **Người chơi trả bằng key OpenRouter của chính họ** [Chốt]. Chủ dự án chỉ trả cho máy chủ và cho bộ đo. Key người chơi được mã hoá khi lưu, không bao giờ ghi vào log hay gửi về trình duyệt (`docs/security.md`). Nên thử luồng kết nối OAuth của OpenRouter để người chơi khỏi phải dán key tay (chưa kiểm luồng này có còn hoạt động không).
- Ước lượng thô ban đầu (giá tháng 10/2026): khoảng 0,05–0,12 USD mỗi chương với model viết tầm trung–cao, dưới 0,01 USD với model rẻ. Chi phí chủ yếu nằm ở token ra của bước viết. Số thật nằm trong các lần chạy ở `evals/results/` (ví dụ `2026-10-20-run-tu-tien-1/`).
- Vẫn cần trần chi phí dù tiền là của người chơi: truyện lỗi lặp vô hạn không được đốt key của họ, và người chơi phải thấy trước mỗi chương tốn khoảng bao nhiêu (ước tính: D-87).
- Mỗi cảnh có tối thiểu 3 lần gọi model (viết, trích, kiểm), có thể thêm 1 lần viết lại.
- Model rẻ cho trích/kiểm/tạo lựa chọn; model viết tiếng Việt tốt hơn cho chương truyện.
- **Trần chi phí mỗi chương và mỗi truyện:** nằm trong `config/limits.yaml` (số tạm, chỉnh sau khi có thêm lần chạy thật); vượt trần thì dừng viết lại và báo.
- Tên model, trần token, trần chi phí nằm trong cấu hình, không viết cứng trong code.

## 11. Công nghệ [Quyết định thiết kế]
- **Backend:** Python, FastAPI, streaming SSE.
- **Frontend:** React + TypeScript + Tailwind, web hiển thị tốt trên điện thoại.
- **Đồ thị:** Neo4j, truy vấn bằng Cypher, **tự viết lớp truy cập** (không dùng thư viện bộ nhớ có sẵn như Graphiti; lý do: `docs/decisions.md`). Phát triển bằng Docker trên máy. Gói AuraDB Free tự tạm dừng sau 3 ngày không dùng và chỉ dành cho dùng thử, nên khi có người chơi thật thì tự chạy Neo4j Community. Bản 1: chồng prod tự chạy trên máy nhà, ra ngoài qua Cloudflare Tunnel (D-103).
- **Dữ liệu khác:** PostgreSQL — tài khoản, truyện, văn bản chương, lựa chọn, nhật ký chi phí, nhật ký người canh.
- **Điều phối chương:** LangGraph (các bước §6.2).
- **LLM:** qua OpenRouter. Model viết chọn bằng bài D (§9): xem `config/models.yaml` và D-33.
- **Vector** (chỉ cho đối thủ số 3 trong bộ đo): dùng gì cũng được [Để người làm quyết].

## 12. Kế hoạch bản 1 (6 tuần, ~10 giờ/tuần, một người)

| Tuần | Làm | Xong khi |
|---|---|---|
| 1 | Thiết kế đồ thị hai lớp; **viết tay** một truyện mẫu 5 chương và dựng đồ thị cho nó bằng tay | Truy vấn Cypher trả lời đúng các câu ở §7.3 trên truyện mẫu |
| 2 | Đường đi một chương (lấy đồ thị → viết → trích); thử model viết; đo chi phí, đặt trần | Chạy liền 10 chương từ dòng lệnh |
| 3 | Người canh (mâu thuẫn + lộ sớm); bộ câu kiểm đầu tiên | Bảng đo lần đầu |
| 4 | Giao diện khởi tạo và chơi, chương chạy dần | Tự chơi hết một truyện ngắn |
| 5 | Sổ tay, hỏi người kể, đăng nhập, lưu truyện | Bạn bè mở link chơi được |
| 6 | Đo với các đối thủ, chỉnh chi phí, sửa lỗi bạn bè báo | Bảng kết quả + README |

Tuần 1 làm tay có chủ ý: thiết kế đồ thị sai thì mọi thứ sau đều sai.

Đánh giá thẳng: 60 giờ cho cả danh sách này là chặt, nhất là cảnh chạy song song (§4.2) và luồng key người chơi. Nếu trễ, giữ thứ tự tuần và lùi mốc, không cắt người canh hay bài đo A.

## 13. Rủi ro
| Rủi ro | Cách giảm |
|---|---|
| Trích thay đổi sai (trùng tên, biệt danh) làm hỏng đồ thị | Chuẩn hoá thực thể bằng danh sách tên + biệt danh có sẵn; người canh kiểm; nhật ký để sửa tay |
| Văn khô vì prompt nhồi quá nhiều sự thật | Chỉ đưa phần đồ thị liên quan; tách "sự thật cần tôn trọng" khỏi "gợi ý nên nhắc tới" |
| Chi phí vượt | Trần trong cấu hình; model rẻ cho mọi bước trừ bước viết |
| Lộ twist qua giao diện | Lọc bằng code theo lớp người chơi biết (§8.3), có test |
| Phạm vi phình | Bản 1 chỉ gồm danh sách §5; mọi thứ khác vào bản sau |
| Tài liệu nguồn nói về người thật (bài báo) — rủi ro bôi nhọ, pháp lý | Mặc định đổi người thật thành nhân vật hư cấu khi trích; cảnh báo người chơi; không cho chia sẻ truyện dựng từ bài báo có người thật (bản 3) |
| Nội dung nhạy cảm do người dùng tự viết | Tuân chính sách của nhà cung cấp model; mức u tối có giới hạn trên; không nội dung tình dục liên quan trẻ vị thành niên |
| Chưa có model kiểm duyệt nào được xác nhận tốt cho tiếng Việt | Tự dựng bộ câu kiểm tiếng Việt (có dấu, không dấu, teencode) và đo trước khi chọn (`docs/security.md`) |
| Lộ key OpenRouter của người chơi | Mã hoá khi lưu, không log, không gửi về trình duyệt; có test |
| Prompt injection lưu trữ: chữ người chơi nằm trong đồ thị rồi quay lại prompt các chương sau | Mọi chữ có nguồn gốc người chơi mang nhãn và luôn được bọc như dữ liệu, kể cả khi đọc ra từ đồ thị |

## 14. Còn mở
- Ai là người dùng thật đầu tiên ngoài chủ dự án, và đưa cho họ bằng cách nào.
- Model kiểm duyệt nội dung cho tiếng Việt: đang dùng tạm một model (`config/models.yaml`, vai `moderate`). Bộ câu giữ riêng v1 đã chạy (`evals/results/2026-10-21-g9-holdout-1/notes.md`) và đã được dùng để đổi cách gọi (D-79), nên thành bộ chỉnh; bộ giữ riêng v2 (`evals/redteam/g9_moderation_holdout_v2.yaml`, D-80) đã chạy (`evals/results/2026-10-21-g9-holdout-v2-1/`). Việc bắt chữ tấn công thật (loại nặng) chưa có cách đo nội bộ: cần bộ red-team công khai có giấy phép (docs/eval.md, G9).
- Nghị định 147/2024/NĐ-CP (xác thực tài khoản bằng số điện thoại cho mạng xã hội) có áp dụng cho một trang truyện tương tác nhỏ không. Chưa kiểm; cần hỏi trước khi mở công khai cho người lạ.
- Luồng OAuth của OpenRouter có dùng được không.
