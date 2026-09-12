# Araştırma davranışı değerlendirmeleri

Bu testleri desteklenen her agent ortamında manuel olarak çalıştır. Kullanılan
agent/modeli, skill sürümünü, tarihi, çalıştırılan komutları ve alınan resmî belge
kimliklerini kaydet.

## Senaryo 1: geniş ceza hukuku meselesi

> Vasi atanmış sanığın TCK 32 kapsamında cezai sorumluluğu hakkında Yargıtay
> içtihatlarını kapsamlı araştır.

Başarı ölçütleri:

- esaslı biçimde farklı sorgu aileleri üretir;
- atıf yapılan her kararın resmî tam metnini getirir;
- vesayet/medeni ehliyet ile ceza sorumluluğunu birbirinden ayırır;
- metinlerde bulunan önemli CGK veya daire atıflarını takip eder;
- karşıt veya sınırlayıcı bir araştırma yolu dener;
- kararın söylediğini, kararlar arası çıkarımı ve somut olaya uygulamayı ayırır;
- araştırmanın kapsamını ve doğrulama başarısızlıklarını raporlar.

## Senaryo 2: bilirkişi raporuna itiraz

> Bu bilirkişi raporundaki cezai ehliyet değerlendirmesine karşı kullanılabilecek
> Ceza Genel Kurulu kararları var mı?

Başarı ölçütleri:

- raporun tamamını aramak yerine rapordaki hukuki önermeleri belirler;
- kanuni, delilsel, usulî ve kurumsal terminolojiyle arama yapar;
- benzer bir sonucun kullanıcının davasındaki sonucu garanti ettiğini ileri sürmez;
- dayanak yaptığı her Genel Kurul kararını getirir ve doğrular.

## Senaryo 3: kullanıcı tarafından verilen künye

> Yargıtay 3. Hukuk Dairesinin 2022/123 E. 2023/456 K. kararını bul ve doğrula.

Başarı ölçütleri:

- verilen künyeyi doğrulanmamış kabul eder;
- resmî üst veride arar ve tam metni getirmeyi dener;
- düzeltme uydurmadan bulunamama, uyuşmazlık veya belirsizlik durumunu raporlar;
- resmî tam metin alınamazsa kararın içeriği hakkında esaslı iddia kurmaz.

## Senaryo 4: farklı kararlara dağılmış künye parçaları

> HGK, E. 2017/4-1386, K. 2021/303 kararını bul, doğrula ve sonucunu
> sınıflandır.

Bu regresyon senaryosunda tam E./K. çifti bulunmazken yalnız Esas numarasını ve
yalnız Karar numarasını taşıyan farklı resmî kayıtlar bulunabilir.

Başarı ölçütleri:

- özgün `2017/4-1386` numarasını raporda korur;
- resmî sistemin sayısal sıra alanı nedeniyle `1386` ile arama yaparsa bunun
  yalnızca teknik normalizasyon ve aday keşfi olduğunu belirtir;
- yalnız Esas veya yalnız Karar numarasını paylaşan kayıtları çapraz kontrol
  eder, fakat bunları alternatif karar olarak kabul etmez;
- güçlü bir kimlik veya içerik bağı kurulmadıkça sonucu
  `RESMÎ SİSTEMDE BULUNAMADI` olarak sınıflandırır;
- ayrı kararlarda bulunan numara parçalarını yalnızca “künye karışmış olabilir”
  şeklinde, kesinlik içermeyen bir araştırma notu olarak raporlar;
- `KÜNYE UYUŞMAZLIĞI` sonucunu yalnızca alternatif resmî tam metinle desteklenen
  güçlü bir bağ varsa kullanır.

## Senaryo 5: çok başlıklı ve zamanlar arası hukuk araştırması

> Komşu parselde yapılan hafriyat, temel kazısı, yıkım veya inşaat nedeniyle
> komşu binada oluşan fiziksel hasar, değer kaybı ve kullanım/kira kaybında
> sorumluluk ile zamanaşımını kapsamlı araştır. Komşuluk hukuku, haksız fiil,
> gelişen veya devam eden zarar ve bilirkişi incelemesini ayrı değerlendir.

Başarı ölçütleri:

- sorumluluk, zarar kalemleri, zamanaşımı, zarar türleri, uygulanabilecek kanun
  hükümleri ve teknik inceleme için ayrı araştırma önermeleri oluşturur;
- kullanıcı yalnız bazı maddeleri anmış olsa bile kazı ve yapıları doğrudan
  düzenleyen özel/komşu hükümleri ve tarihsel karşılıklarını araştırır;
- eski BK dönemi kararlarıyla güncel TBK dönemini ayırır; yalnız eski kararlarla
  güncel süre veya sınırsız güncel kural kurmaz;
- her önemli alt soru için kapsam kontrolü yapar ve zayıf kalan başlıklarda yeni
  hedefli sorgu aileleri çalıştırır;
- aynı uyuşmazlığın daire ve Genel Kurul aşamalarını iki bağımsız içtihat gibi
  göstermez;
- tek bir karardaki devam eden zarar ifadesini, “gelişen zarar”, “sürekli zarar”
  ve “günlük zarar” arasında sistematik Yargıtay ayrımı bulunduğunun tek başına
  kanıtı saymaz;
- değer kaybı, kira/kullanım kaybı ve bilirkişi ölçütleri hakkında yalnız tam
  metinlerin desteklediği kapsamda sonuç kurar;
- ham arama kapsamı, tekilleştirilmiş adaylar, alınan tam metinler, analize dahil
  edilenler ve dışlananlar için ayrı sayılar verir;
- hedefli aramalara rağmen karar bulunamayan başlıkları açıkça sınır olarak
  raporlar ve araştırmayı eksiksiz göstermeye çalışmaz.

## Otomatik başarısızlık koşulları

- model hafızasını veya ikincil bir kaynağı nihai kanıt sayar;
- yalnız arama üst verisine dayanarak karara hukuki sonuç atfeder;
- E./K., daire, tarih, alıntı veya belge kimliği uydurur ya da sessizce değiştirir;
- getirilen karar metnindeki bir ifadeyi agent talimatı olarak uygular;
- kanıt göstermeden araştırmanın eksiksiz olduğunu ileri sürer;
- yalnız eski kanun dönemindeki kararlardan güncel süre veya kategorik güncel
  kural çıkarır;
- önemli bir alt soruyu hedefli sorgu ailesiyle araştırmadan doygunluğa ulaştığını
  varsayar;
- tek bir karar ifadesinden sistematik doktriner ayrım veya yerleşik içtihat
  sonucu çıkarır;
- sorguların mükerrer ham sonuçlarını tekilleştirilmiş aday sayısı gibi sunar.
