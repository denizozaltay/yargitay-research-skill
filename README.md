# Yargıtay Research Skill

Resmî Yargıtay Karar Arama sistemi üzerinde kapsamlı, iteratif ve doğrulanabilir
içtihat araştırması yapmayı agent'a öğreten taşınabilir bir Agent Skill.

Güncel istemci sürümü: **1.0.0**

Bu proje bir karar listesi veya hukuk yorumu servisi değildir. Skill araştırma
stratejisini tanımlar; beraberindeki Python istemcisi yalnızca resmî kaynaktan
arama sonuçlarını ve karar tam metinlerini güvenilir, makinece okunabilir şekilde
getirir.

## Neden bu skill var?

AI modelleri ve ikincil hukuk kaynakları bazen son derece inandırıcı görünen
fakat yanlış E/K numaraları, hatalı olay özetleri veya karar metninde bulunmayan
sözde alıntılar üretebilir. Bu skill, Yargıtay'a atfedilecek her kararı resmî
karar bankasında bulmayı, tam metnini doğrulamayı ve yalnız bundan sonra hukuki
analizde kullanmayı amaçlar.

## Agent için kurulum

Bu GitHub reposunun kök URL'sini ChatGPT Work, Codex, Claude Code veya Agent
Skills destekleyen başka bir agent'a verip şunu söyleyin:

```text
Bu repodaki Yargıtay araştırma skill'ini kur ve Yargıtay araştırmalarında kullan.
```

Agent, dağıtılabilir skill'i `skills/yargitay-research/` altında bulmalıdır.
Kurarken bu klasörü içeriğiyle birlikte korumalı ve `SKILL.md` dosyasını giriş
noktası olarak kullanmalıdır. Root README, testler ve CI skill paketine dahil
değildir.

Manuel kurulum gerekiyorsa `skills/yargitay-research/` klasörünü agent
ortamınızın skill dizinine kopyalayın.

## Temel güvence

Skill şu kaynak politikasını uygular:

- Model hafızası, kullanıcı tarafından verilen künye ve ikincil hukuk siteleri
  yalnızca araştırma ipucudur.
- Bir kararın hukuki sonucu veya gerekçesi, resmî Yargıtay tam metni alınmadan
  kullanılmaz.
- Resmî kaynaktan doğrulanamayan karar emsal olarak sunulmaz; doğrulama sorunu
  açıkça belirtilir.
- Kararın söylediği husus, kararlar arasından çıkarılan eğilim ve agent'ın somut
  olaya ilişkin değerlendirmesi birbirinden ayrılır.

## Gereksinimler

- Python 3.10 veya üzeri
- İnternet erişimi

Harici Python paketi gerekmez. MCP, tarayıcı otomasyonu, veritabanı ve LLM API
bağımlılığı yoktur.

## Komutlar

```bash
cd skills/yargitay-research
python scripts/yargitay.py health
python scripts/yargitay.py search --query '"TCK 32" "akıl hastalığı"'
python scripts/yargitay.py search-all --query '"vesayet" "cezai sorumluluk"' --max-results 100
python scripts/yargitay.py get DOCUMENT_ID
```

Arama; daire/kurul, Esas/Karar numarası aralıkları ve karar tarihi aralığıyla
filtrelenebilir. Tüm seçenekler için:

```bash
python scripts/yargitay.py search --help
```

Komut sonuçlarının stdout çıktısı JSON'dur (`--help` insan tarafından okunabilir
yardım metnidir). Başarılı çıktılarda `ok: true`; beklenen hatalarda `ok: false`
ve kararlı bir hata nesnesi bulunur.

## Cache ve erişim sınırları

Karar tam metinleri varsayılan olarak işletim sisteminin kullanıcı cache
dizininde saklanır. `YARGITAY_CACHE_DIR`, `--cache-dir`, `--no-cache` ve
`get --refresh` seçenekleriyle davranış değiştirilebilir.

Cache dosyaları karar tam metni içerebilir. Kişisel veri veya hassas dosyalarla
çalışılan ortamlarda `--no-cache` kullanın ve yerel veri saklama politikanızı
uygulayın.

İstemci resmî sisteme yük bindirmemek için istekleri varsayılan olarak en az üç
saniye aralıkla gönderir. Bu aralık ayrı CLI süreçleri arasında da korunur;
`--no-cache` karar metni cache'ini kapatır, erişim sınırlayıcısını kapatmaz.
İstemci 429, resmî JSON hata zarfı ve geçici sunucu hatalarında sınırlı geri
çekilme uygular. Toplu aramalar `--max-results` ile sınırlandırılır.

## Proje yapısı

```text
skills/yargitay-research/
├── SKILL.md
├── agents/openai.yaml
├── scripts/yargitay.py
└── references/
    ├── research-method.md
    ├── verification-and-citation.md
    └── yargitay-api.md
```

## Önemli teknik uyarı

`karararama.yargitay.gov.tr` resmî bir developer API yayımlamamaktadır. İstemci,
sitenin kendi frontend'inin kullandığı belgelenmemiş HTTP endpointleriyle
çalışır. Endpoint veya yanıt şeması haber verilmeden değişebilir. `health`
komutu erişimi ve beklenen arama şemasını kontrol eder; `schema_changed` hatası
alındığında `references/yargitay-api.md` içindeki kontrollü teşhis akışı
izlenmelidir. Resmî sistemin HTTP 200 içinde döndürdüğü hata zarfları önce hata
türü bakımından incelenir ve doğrudan şema değişikliği sayılmaz.

Bu proje Yargıtay Başkanlığı tarafından geliştirilmemiş veya onaylanmamıştır.
Karar metinleri resmî kaynağa aittir. Çıktılar hukuki bilgi amaçlıdır ve somut
dosyayı inceleyen bir hukukçunun danışmanlığının yerini tutmaz.

## Geliştirme

```bash
python -m pip install -r requirements-dev.txt
ruff check skills tests
python -m unittest discover -s tests -v
python -m compileall -q skills tests
```

Canlı entegrasyon testi her commit'te çalıştırılmaz. Resmî servise yönelik
testler düşük sıklıkta ve erişim sınırlarına saygılı biçimde yürütülmelidir.

## Lisans

[MIT](LICENSE)
