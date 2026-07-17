# 📋 Bộ Câu Hỏi Đánh Giá Chatbot Tư Vấn Học Vụ – Đại học Cần Thơ

> **Mục đích:** Đánh giá độ chính xác, khả năng nhận diện ngành, xử lý viết tắt,
> hiểu ngữ cảnh hội thoại, và khả năng từ chối bịa đặt của chatbot.
>
> **Thang điểm gợi ý:** Mỗi câu cho điểm 0–5 theo tiêu chí:
> - **5** – Trả lời đúng, đầy đủ, trình bày rõ ràng
> - **4** – Đúng nhưng thiếu 1–2 chi tiết nhỏ
> - **3** – Đúng chủ yếu nhưng có sai sót hoặc thiếu nhiều chi tiết
> - **2** – Hiểu đúng câu hỏi nhưng nội dung sai nhiều
> - **1** – Nhận diện sai ngành / câu hỏi nhưng không bịa đặt
> - **0** – Bịa đặt thông tin không có trong CSDL

---

## PHẦN A – NHẬN DIỆN VIẾT TẮT & NGÀNH HỌC (14 câu)

*Mục tiêu: Kiểm tra khả năng hiểu viết tắt và định danh đúng ngành, bao gồm CLC/TT.*

### A1. Viết tắt ngành đơn

| # | Câu hỏi | Ngành cần nhận diện | Đáp án tham khảo |
|---|---------|---------------------|-----------------|
| A1-1 | `ktpm học những gì?` | Kỹ thuật Phần mềm | Mô tả chương trình KTPM: 161 TC, 4,5 năm, bằng Kỹ sư |
| A1-2 | `cntt bao nhiêu tín chỉ?` | Công nghệ thông tin | 161 tín chỉ |
| A1-3 | `httt có mã ngành là gì?` | Hệ thống thông tin | 7480104 |
| A1-4 | `khmt đào tạo bao lâu?` | Khoa học Máy tính | 4,5 năm |
| A1-5 | `attt học ở khoa nào?` | An toàn thông tin | Khoa Mạng máy tính và Truyền thông |
| A1-6 | `qtkd văn bằng gì?` | Quản trị kinh doanh | Cử nhân, 141 TC, 4 năm |
| A1-7 | `ktoan mấy năm?` *(chính tả lạ)* | Kế toán | 4 năm, 141 TC, Cử nhân |

### A2. Viết tắt chương trình đặc biệt (CLC / TT)

| # | Câu hỏi | Ngành cần nhận diện | Đáp án tham khảo |
|---|---------|---------------------|-----------------|
| A2-1 | `ktpm clc` | KTPM – Chương trình CLC | 168 TC, 4,5 năm, mã 7480103C |
| A2-2 | `cntt clc học gì?` | CNTT – Chương trình CLC | Thông tin chương trình CLC của CNTT |
| A2-3 | `httt clc bao nhiêu tín chỉ?` | HTTT – Chương trình CLC | Số TC chương trình CLC của HTTT |
| A2-4 | `ktpm clc khác gì ktpm thường?` | Cả hai ngành | So sánh: CLC 168 TC vs thường 161 TC; yêu cầu tiếng Anh B2 |
| A2-5 | `ngành ktpm chất lượng cao` | KTPM – Chương trình CLC | Thông tin đầy đủ chương trình CLC |
| A2-6 | `cntt tt` *(tiên tiến)* | CNTT – Chương trình TT | Thông tin chương trình tiên tiến (nếu có) hoặc báo không có |
| A2-7 | `thú y clc` | Thú y – CTCLC | Mã 7640101C, thông tin chương trình CLC ngành Thú y |

---

## PHẦN B – THÔNG TIN CHƯƠNG TRÌNH ĐÀO TẠO (15 câu)

*Mục tiêu: Kiểm tra độ chính xác khi trả lời chi tiết về các ngành cụ thể.*

### B1. Thông tin cơ bản ngành

| # | Câu hỏi | Đáp án tham khảo (từ dữ liệu) |
|---|---------|-------------------------------|
| B1-1 | `Ngành Kỹ thuật Phần mềm có bao nhiêu tín chỉ?` | 161 tín chỉ |
| B1-2 | `Mã ngành Công nghệ thông tin là gì?` | 7480201 |
| B1-3 | `Ngành Kế toán đào tạo bao lâu và bằng gì?` | 4 năm, Cử nhân |
| B1-4 | `Ngành Quản trị kinh doanh thuộc khoa nào?` | Khoa Quản trị kinh doanh, Trường Kinh tế |
| B1-5 | `Ngành KTPM CLC yêu cầu tiếng Anh đầu ra ở mức nào?` | Bậc 4 / B2 (theo PLO3 của CTCLC) |

### B2. Chuẩn đầu ra & Mục tiêu

| # | Câu hỏi | Đáp án tham khảo |
|---|---------|-----------------|
| B2-1 | `Chuẩn đầu ra ngành KTPM gồm những mục nào?` | Liệt kê PLO1–PLO10+ (đầy đủ) |
| B2-2 | `Mục tiêu đào tạo của ngành CNTT là gì?` | Trích mục tiêu chung & PEOs |
| B2-3 | `Ngành KTPM CLC đào tạo ra kỹ sư hay cử nhân?` | Kỹ sư |
| B2-4 | `Ngành Kế toán có những vị trí việc làm nào sau tốt nghiệp?` | Liệt kê từ phần vị trí việc làm |

### B3. Kế hoạch học tập

| # | Câu hỏi | Đáp án tham khảo |
|---|---------|-----------------|
| B3-1 | `Học kỳ 1 ngành KTPM gồm những môn gì?` | Liệt kê HK1 từ kế hoạch học tập |
| B3-2 | `Ngành CNTT CLC có môn học bằng tiếng Anh không?` | Tùy dữ liệu — trả lời có/không rõ ràng |
| B3-3 | `Ngành KTPM có môn Trí tuệ nhân tạo không?` | Kiểm tra kế hoạch học tập |
| B3-4 | `Ngành Quản trị kinh doanh học mấy kỳ?` | 4 năm × 3 HK/năm = ~12 HK thường + HK3 |
| B3-5 | `Cho tôi xem danh sách môn học năm 3 ngành KTPM` | Liệt kê đầy đủ HK5, HK6 (năm 3) |

---

## PHẦN C – QUY CHẾ HỌC VỤ (12 câu)

*Mục tiêu: Kiểm tra khả năng truy xuất đúng thông tin quy chế.*

| # | Câu hỏi | Đáp án tham khảo (từ quy chế) |
|---|---------|-------------------------------|
| C1 | `Một tín chỉ tương đương bao nhiêu giờ?` | 50 giờ học tập định mức |
| C2 | `Mỗi học kỳ kéo dài bao nhiêu tuần?` | 15 tuần (11 dạy học + 4 thi) |
| C3 | `Điều kiện để được xét học bổng khuyến khích?` | ≥12 TC, kết quả ≥ khá, không HP dưới D, không bị kỷ luật |
| C4 | `Học bổng xuất sắc cần điều kiện gì?` | ĐTBCHK và ĐRL đạt loại xuất sắc |
| C5 | `Nếu không đóng học phí 2 kỳ liên tiếp thì sao?` | Bị buộc thôi học |
| C6 | `Sinh viên có thể học tối đa bao nhiêu năm cho chương trình 4,5 năm?` | 9 năm |
| C7 | `Học kỳ 2 bắt đầu từ tuần nào?` | Tuần thứ 01 đến tuần thứ 17 (bao gồm 2 tuần nghỉ Tết) |
| C8 | `Điều kiện để chuyển ngành là gì?` | Không năm 1/năm cuối, đạt điểm trúng tuyển, còn thời gian... |
| C9 | `Học phần tiên quyết là gì?` | Học phần phải tích lũy trước mới được đăng ký HP kế tiếp |
| C10 | `Học phần điều kiện có tính vào điểm TBC tích lũy không?` | Không tính vào ĐTBCTL |
| C11 | `SV có thể học online tối đa bao nhiêu % chương trình?` | Không quá 30% |
| C12 | `Đối tượng được hưởng trợ cấp xã hội là ai?` | SV dân tộc ít người vùng cao; mồ côi; tàn tật >41%; hộ nghèo |

---

## PHẦN D – SO SÁNH & PHÂN TÍCH (6 câu)

*Mục tiêu: Kiểm tra khả năng tổng hợp thông tin từ nhiều ngành/nguồn.*

| # | Câu hỏi | Ghi chú đánh giá |
|---|---------|-----------------|
| D1 | `So sánh ngành KTPM và CNTT, nên học ngành nào?` | Phải trình bày được điểm khác biệt; không đưa ra lời khuyên chủ quan |
| D2 | `Ngành nào trong khối CNTT có nhiều tín chỉ nhất?` | So sánh KTPM(161), CNTT(161), HTTT, KHMT, ATTT... |
| D3 | `Các ngành có chương trình CLC ở CTU là những ngành nào?` | Liệt kê đủ các file _CTCLC trong CSDL |
| D4 | `KTPM CLC và KTPM thường khác nhau điểm gì?` | TC (168 vs 161), yêu cầu ngoại ngữ, tên văn bằng giống nhau |
| D5 | `Ngành Kế toán và Kiểm toán khác nhau như thế nào?` | Trình bày 2 ngành riêng biệt |
| D6 | `Các ngành thuộc Trường Kinh tế có những ngành nào?` | Tổng hợp từ metadata don_vi |

---

## PHẦN E – HỘI THOẠI NGỮ CẢNH / MULTI-TURN (6 câu)

*Mục tiêu: Kiểm tra khả năng nhớ ngữ cảnh từ câu trước.*

> **Cách thực hiện:** Gõ lần lượt từng câu, KHÔNG bắt đầu chat mới giữa các câu trong cùng nhóm.

### Nhóm E1 – Hỏi tiếp về ngành vừa hỏi

```
Lượt 1: "ktpm clc học gì?"
Lượt 2: "bao nhiêu tín chỉ?"         → phải hiểu là hỏi KTPM CLC (168 TC)
Lượt 3: "kế hoạch học tập kỳ 1 như thế nào?"  → vẫn trong ngữ cảnh KTPM CLC
```

### Nhóm E2 – Chuyển chủ đề

```
Lượt 1: "ngành kế toán có mấy tín chỉ?"
Lượt 2: "còn ngành kiểm toán?"       → phải chuyển sang Kiểm toán
Lượt 3: "hai ngành này khác nhau thế nào?"  → so sánh cả hai
```

---

## PHẦN F – TỪ CHỐI BỊA ĐẶT / NGOÀI PHẠM VI (7 câu)

*Mục tiêu: Chatbot PHẢI từ chối, KHÔNG được bịa thông tin.*

| # | Câu hỏi | Đáp án mong đợi |
|---|---------|-----------------|
| F1 | `Học phí ngành KTPM năm 2025 là bao nhiêu?` | Từ chối — học phí do Hiệu trưởng quyết định, không có số cụ thể |
| F2 | `Điểm chuẩn ngành CNTT năm 2025 là bao nhiêu?` | Từ chối — không có trong CSDL |
| F3 | `CTU có ký túc xá không, giá thuê bao nhiêu?` | Từ chối — không có trong CSDL |
| F4 | `Ngành Bác sĩ đa khoa học ở CTU như thế nào?` | Từ chối — không có trong CSDL hiện tại |
| F5 | `Giáo sư Nguyễn Văn A dạy môn gì?` | Từ chối — không có thông tin giảng viên |
| F6 | `Trường ĐH Cần Thơ thành lập năm nào?` | Từ chối hoặc nói không có trong dữ liệu hiện tại |
| F7 | `ktpm clc tt` *(vô nghĩa — vừa CLC vừa TT)* | Xử lý gracefully — hỏi lại hoặc hiểu một trong hai |

---

## PHẦN G – CHÍNH TẢ & TIẾNG ANH (4 câu)

*Mục tiêu: Chatbot có chịu được câu hỏi lỗi chính tả / hỏi tiếng Anh không.*

| # | Câu hỏi | Ghi chú |
|---|---------|---------|
| G1 | `nganh ky thuat phan mem co may tin chi` *(không dấu)* | Phải nhận diện được KTPM |
| G2 | `Ky thuat phan mem clc` *(không dấu + CLC)* | Phải nhận diện KTPM CLC |
| G3 | `What is the curriculum of Software Engineering?` | Tùy — có thể trả lời tiếng Việt hoặc tiếng Anh |
| G4 | `ktpm hoc nhung mon gi ` *(có dấu cách thừa cuối)* | Phải xử lý được |

---

## 📊 Bảng Tổng Hợp Kết Quả

| Phần | Số câu | Điểm tối đa | Điểm đạt được | Tỉ lệ % |
|------|--------|-------------|---------------|---------|
| A – Nhận diện viết tắt | 14 | 70 | | |
| B – Thông tin CTĐT | 15 | 75 | | |
| C – Quy chế học vụ | 12 | 60 | | |
| D – So sánh & Phân tích | 6 | 30 | | |
| E – Hội thoại ngữ cảnh | 6 | 30 | | |
| F – Từ chối bịa đặt | 7 | 35 | | |
| G – Chính tả & Tiếng Anh | 4 | 20 | | |
| **Tổng** | **64** | **320** | | |

---

## 📌 Hướng Dẫn Sử Dụng

1. **Chạy server chatbot** trước khi test: `python src/api.py`
2. **Test tuần tự** từ Phần A → G
3. **Ghi lại câu trả lời thực tế** vào cột "Kết quả" riêng
4. **Chú ý đặc biệt** với Phần F — nếu chatbot bịa đặt → 0 điểm ngay
5. **Phần E** phải test trong 1 session liên tục (không reset chat)

> **Ngưỡng đánh giá:**
> - ≥ 80% → Chatbot hoạt động tốt ✅
> - 60–80% → Cần cải thiện một số trường hợp ⚠️
> - < 60% → Cần xem lại dữ liệu hoặc logic ❌
