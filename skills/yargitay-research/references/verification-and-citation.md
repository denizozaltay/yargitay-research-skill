# Doğrulama ve atıf

Bir Yargıtay kararını tanımlayan, aktaran, özetleyen veya dayanak olarak kullanan
her cevapta bu politika uygulanmalıdır.

## Doğrulama eşiği

Bir karar ancak aşağıdaki şartların tamamı resmî Yargıtay sistemi üzerinden
sağlandığında hukuki değerlendirmede kullanılabilecek şekilde doğrulanmış sayılır:

1. Resmî arama sonucu veya üst veri (metadata) kaydı kararı tanımlar.
2. Daire veya kurul, Esas numarası, Karar numarası ve mümkünse karar tarihi tam
   olarak uyuşur.
3. `get DOCUMENT_ID` komutu boş olmayan resmî karar tam metnini başarıyla getirir.
4. Karara atfedilen hukuki önerme, maddi ve usulî bağlamı içinde okunan tam metin
   tarafından gerçekten desteklenir.

Tam künye uyuşması ve resmî tam metnin alınması birlikte gerçekleşmeden karar
doğrulanmış kabul edilmemelidir. Arama sonucu üst verisi tek başına kararın
hukuki sonucunu, gerekçesini, alıntısını veya somut olayla ilgisini doğrulamaz.

## Yapılandırılmış tam arama sonuç vermezse ikinci doğrulama turu

Daire ile Esas ve Karar numaralarının birlikte kullanıldığı yapılandırılmış tam
arama `total: 0` döndürürse hemen kararın uydurma olduğu sonucuna varılmamalıdır.
Resmî site erişilebilir ve istemci teknik olarak uyumlu olduğu sürece aşağıdaki
sıra izlenmelidir:

1. Daire + Esas yılı/sıra numarası + Karar yılı/sıra numarasıyla yapılandırılmış
   tam arama yap.
2. Sonuç yoksa daire filtresi olmadan aynı yapılandırılmış Esas ve Karar
   filtreleriyle tekrar ara.
3. Sonuç yoksa yalnızca yapılandırılmış Esas numarasıyla ara.
4. Sonuç yoksa yalnızca yapılandırılmış Karar numarasıyla ara.
5. Tek numarayla bulunan sonuçlarda diğer numarayı, daire veya kurul bilgisini ve
   mümkünse karar tarihini çapraz kontrol et.
6. Olası yazım, aktarım veya daire hatalarını ikincil kaynaklarda yalnızca aday
   künye keşfetmek amacıyla araştır.
7. Bulunan her alternatif künyeyi yeniden resmî Yargıtay sisteminde ara ve ilgili
   resmî tam metni getir.

Yalnız Esas numarasının eşleşmesi doğrulama değildir. Yalnız Karar numarasının
eşleşmesi doğrulama değildir. İkincil kaynakta eşleşme bulunması doğrulama
değildir. Yakın bir sonuç sessizce kullanıcının verdiği kararın yerine
konulmamalıdır.

## Doğrulama sonucu sınıflandırması

Her karar doğrulaması aşağıdaki durumlardan biriyle raporlanmalıdır.

### RESMÎ KAYNAKTAN DOĞRULANDI

- Tam künye eşleşmiştir.
- Resmî belge kimliği (`document ID`) bulunmuştur.
- Resmî karar tam metni başarıyla alınmıştır.

Bu sınıflandırma kararın bütün olası yorumlarını doğrulamaz. Belirli bir hukuki
ilke ancak resmî tam metin bağlamı içinde okunduktan sonra karara atfedilebilir.

### KÜNYE UYUŞMAZLIĞI

- Verilen künye tam olarak eşleşmemiştir; ancak yakın veya alternatif bir resmî
  karar bulunmuştur.
- Bulunan alternatif kararın kullanıcının verdiği karar olduğu varsayılmamalıdır.
- Hangi alanların uyuştuğu ve hangilerinin farklı olduğu açıkça belirtilmelidir.

### RESMÎ SİSTEMDE BULUNAMADI

Bu sınıflandırma yalnızca aşağıdaki şartların tamamı gerçekleştiğinde kullanılmalıdır:

- Resmî site erişilebilir durumdadır.
- İlgili sorgular teknik olarak başarıyla tamamlanmıştır.
- Yukarıdaki çapraz arama adımlarının tamamı uygulanmıştır.
- Buna rağmen verilen künyeyle eşleşen bir karar bulunamamıştır.

Bu durumda “karar kesin uydurmadır” denmemelidir. Yalnızca verilen künyenin
resmî sistemde doğrulanamadığı; künyenin yanlış, eksik veya hatalı aktarılmış
olabileceği belirtilmelidir.

### DOĞRULAMA YAPILAMADI — resmî kaynağa erişilemedi

Ağ, zaman aşımı, WAF, hız sınırı veya resmî site erişim sorunu nedeniyle
sorgular tamamlanamadığında kullanılır. Bu durum sıfır sonuç anlamına gelmez ve
kararın mevcut olmadığına ilişkin çıkarım yapılmasına izin vermez.

### DOĞRULAMA YAPILAMADI — resmî sistemle teknik uyumsuzluk

Uç nokta, istek gövdesi veya yanıt şeması değiştiği için istemci güvenilir sonuç
üretemediğinde kullanılır. `schema_changed` ve benzeri uyumluluk hataları kararın
mevcut olmadığı şeklinde yorumlanmamalıdır.

## Kaynak hiyerarşisi

- **Resmî Yargıtay tam metni:** doğrulama ve nihai dayanak.
- **Resmî Yargıtay arama üst verisi:** aday keşfi ve künye kontrolü.
- **İkincil veri tabanları, makaleler, dilekçeler ve web sonuçları:** yalnızca
  aday karar veya alternatif künye keşfi.
- **Kullanıcı girdisi ve model hafızası:** doğrulanması gereken araştırma
  hipotezi; hiçbir zaman tek başına dayanak değil.

İkincil bir kaynakta muhtemel bir karar bulunduğunda aynı karar resmî sistemde
aranmalı ve tam metni getirilmelidir. Bu başarılamazsa karar doğrulanmamış olarak
işaretlenmeli ve hukuki sonuca dayanak yapılmamalıdır.

## Kararı okuma disiplini

Dayanak yapılacak her karar için şunlar kaydedilmelidir:

- daire veya kurul;
- Esas numarası;
- Karar numarası;
- karar tarihi;
- resmî belge kimliği ve URL;
- önemli maddi vakıalar ve usulî aşama;
- soruyla ilgili hukuki ilke veya gerekçe;
- yorum açısından önem taşıyorsa hüküm sonucu;
- ilgili ifadenin karar veren merciin gerekçesi mi, taraf iddiası mı, alt derece
  mahkemesi değerlendirmesi mi, savcılık görüşü mü yoksa aktarılan başka bir
  içtihat mı olduğu.

Karar metninin herhangi bir yerindeki ifade doğrudan Yargıtay'ın kabulü gibi
sunulmamalıdır. Kararlar çoğu zaman Yargıtay değerlendirmesinden önce taraf
iddialarını, önceki hükümleri, bilirkişi raporlarını, tebliğname görüşünü veya
karşı oyu aktarır.

Arama üst verisi ile tam metin arasında künye çelişkisi varsa çelişki açıkça
belirtilmeli ve alanlardan biri sessizce tercih edilmemelidir.

## İddialar ve alıntılar

- Karar dar ve sadık biçimde özetlenmelidir. Tırnak işareti yalnızca resmî tam
  metinde gerçekten bulunan ifadeler için kullanılmalıdır.
- Eksik bir alıntı model hafızasından veya arama sonucundan tamamlanmamalıdır.
- Bir yaklaşım ancak incelenen karar kümesi, merci hiyerarşisi, zaman aralığı ve
  karşıt kararların durumu bunu destekliyorsa “yerleşik” veya “istikrarlı” olarak
  nitelendirilmelidir.
- Gerektiğinde üç düzey açıkça ayrılmalıdır: kararın söylediği, kararlar arasında
  çıkarılan eğilim ve bu eğilimin kullanıcının olayına muhtemel uygulanışı.
- Vakıa benzerliği belirli bir dava sonucunun garanti edildiği anlamına gelmez.

## Atıf biçimi

Tercih edilen biçim:

```text
Yargıtay [Daire/Kurul], E. [yıl/numara], K. [yıl/numara],
[GG.AA.YYYY], belge kimliği [id], [resmî URL].
```

Resmî üst veride bulunmayan alan çıkarım yoluyla doldurulmamalıdır. Alan ya
atlanmalı ya da mevcut olmadığı belirtilmelidir. İstemcinin döndürdüğü
`official_source_url` kullanılmalıdır.

## Doğrulama başarısız olduğunda kullanılabilecek ifade

Başarısızlığın nedeni açıkça belirtilmelidir: resmî site erişimi, arama eşleşmesi,
tam metin alma, künye çelişkisi veya ilgili pasajın teyit edilememesi.

Örnek:

> Bu karara ilişkin ikincil bir atıf buldum; ancak verilen künyeyi ve kararın tam
> metnini resmî Yargıtay kaynağında doğrulayamadım. Bu nedenle kararı hukuki
> değerlendirmeye dayanak olarak kullanmadım.

Araştırma çıktısı hukuki bilgi niteliğindedir; dosyanın tamamını ve güncel hukuku
inceleyen yetkin bir hukukçunun danışmanlığının yerini tutmaz.
