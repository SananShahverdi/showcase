import type { TranslationDictionary } from "../types";

export const az = {
  meta: {
    title: "Effekt — Su, istilik və işıq",
    description:
      "Effekt material, su və işıq vasitəsilə hamamları, sağlamlıq interyerlərini, saunaları, hovuzları və nəm məkanlar üçün seçilmiş sistemləri təqdim edir.",
  },
  localeSwitcher: {
    label: "Dil",
    ariaLabel: "Dili seçin",
  },
  navigation: {
    primaryAriaLabel: "Əsas naviqasiya",
    footerAriaLabel: "Səhifənin alt naviqasiyası",
    portfolio: "Portfolio",
    about: "Haqqımızda",
    backToTop: "Yuxarı qayıt ↑",
    homeAriaLabel: "Effekt — ana səhifə",
    backToTopAriaLabel: "Effekt — yuxarı qayıt",
  },
  hero: {
    eyebrow: "Hamamlar · Sağlamlıq · Saunalar · Hovuzlar · Sistemlər",
    titleBeforeEmphasis: "Su, istilik və ",
    titleEmphasis: "işıq",
    titleAfterEmphasis: "\u2060—formaya çevrilir.",
    support:
      "Effekt hamamları, sağlamlıq interyerlərini, saunaları, hovuzları və nəm məkanlar üçün seçilmiş sistemləri material, hərəkət və işıq vasitəsilə təqdim edir.",
    explore: "Portfolionu kəşf edin",
    about: "Effekt haqqında",
  },
  water: {
    outline: "Kontur",
    motionReduced: "Hərəkət azaldılıb",
    play: "Suyu hərəkətə gətir",
    pause: "Suyu dayandır",
    interactionAll:
      "Su səthində hərəkət edin — tezlik hər bir layihənin konturunu üzə çıxarır",
    interactionDiscipline:
      "Su səthində hərəkət edin — tezlik «{label}» konturunu üzə çıxarır",
    screenReaderDescription:
      "Dekorativ su göstəricinin hərəkətinə cavab verərək layihələrdən ilhamlanan konturları üzə çıxarır. Beş istiqamətin hamısı və onların təsvirləri mətn şəklində də verilib.",
  },
  manifesto: {
    eyebrow: "Effekt / Material indeksi",
    atmosphere:
      "Su, istilik, konstruksiya və işıqlandırma vahid atmosferdə.",
    statement: [
      "Su işığı özündə saxlayır.",
      "Daş ritmi müəyyənləşdirir.",
      "Taxta istiliyi qoruyur.",
    ],
    materials: [
      { id: "water", label: "Su", detail: "Əks · hərəkət" },
      { id: "mosaic", label: "Mozaika", detail: "Naxış · səth" },
      { id: "stone", label: "Daş", detail: "Kütlə · kənar" },
      { id: "timber", label: "Taxta", detail: "İstilik · toxunuş" },
    ],
  },
  portfolio: {
    eyebrow: "Seçilmiş portfolio",
    title: "Su və termal məkanlar fəaliyyət sahələrinə görə sıralanıb.",
    introduction:
      "Tamamlanmış işlər, obyekt sənədləşməsi, icra mərhələsində olan işlər və memarlıq vizuallaşdırmaları aydın şəkildə işarələnib. Hər qalereya arxivdə təsdiqlənmiş layihə qrupuna əsaslanır.",
    disciplinesAriaLabel: "Portfolio istiqamətləri",
    disciplineEyebrow: "Effekt istiqaməti",
  },
  systemsIntro: {
    eyebrow: "İmkanların nümunələri / dörd layihə",
    title: "Atmosfer suyun gizlətdiklərindən asılıdır.",
    description:
      "Bu materiallar ayrı-ayrı layihələrdə görünən nəticələri və quraşdırma detallarını göstərir. Onlar uydurma vahid mühəndislik layihəsi kimi deyil, ayrı-ayrılıqda təqdim olunur.",
  },
  craft: {
    eyebrow: "Material və proses",
    title: "Naxış sudan əvvəl yaranır.",
    description:
      "Mozaika hovuz doldurulmazdan və su səthi əks etdirməyə başlamazdan əvvəl hissə-hissə yığılır, dəqiqliklə düzülür və quraşdırılır.",
    caption: "Fərdi mozaika · emalatxana görünüşü",
    imageAlts: [
      "Boş hovuzun döşəməsində yığılan çiçək naxışlı mozaika.",
      "Emalatxana döşəməsində əl ilə düzülmüş mavi delfin mozaika panelinin yaxın görünüşü.",
    ],
  },
  about: {
    eyebrow: "Effekt haqqında",
    titleLineOne: "Su,",
    titleLineTwo: "formaya çevrilir.",
    paragraphOne:
      "Effekt hamamlar, sağlamlıq məkanları, saunalar, hovuzlar və nəm məkanlar üçün seçilmiş sistemlər ətrafında formalaşan işlər toplusunu təqdim edir.",
    paragraphTwo:
      "Arxiv obyekt fotoqrafiyasını, icra mərhələsində olan işləri və memarlıq vizuallaşdırmalarını birləşdirir; hər biri aydın şəkildə qeyd olunub.",
  },
  footer: {
    statementLineOne: "Su, istilik",
    statementLineTwo: "və işıq—formaya çevrilir.",
    copyright: "Effekt · {year}",
  },
  gallery: {
    close: "Bağla",
    previous: "Əvvəlki",
    next: "Növbəti",
    viewGallery: "Qalereyaya bax · {count}",
  },
  common: {
    archiveCluster: "Arxiv qrupu",
    visibleMaterials: "Görünən materiallar",
    waterHeat: "Su / istilik",
    mediaLabels: {
      "Site photography": "Obyekt fotoqrafiyası",
      Visualization: "Vizuallaşdırma",
    },
    stages: {
      "Built work": "Tamamlanmış iş",
      "Site documentation": "Obyekt sənədləşməsi",
      "Work in progress": "İcra mərhələsi",
      "Final fit-out": "Son tamamlama mərhələsi",
      "Design study": "Dizayn araşdırması",
    },
  },
  a11y: {
    skipWaterIntro: "İnteraktiv su girişini keç",
    openGallery: "«{title}» layihəsinin fotoqalereyasını aç",
    openImage: "«{title}» layihəsinin {index} nömrəli şəklini aç",
    offerings: "{title}: təklif olunan xidmətlər",
  },
  disciplines: {
    "baths-hammams": {
      navLabel: "Hamamlar",
      title: "Hamamlar",
      offerings: ["Türk hamamları", "Şərq hamamları", "Azərbaycan hamamları"],
      introduction:
        "Günbəzlər, qızdırılan daş, yuyunma çanaqları və mozaika—su, ritual və işıqla formalaşan hamam məkanları.",
      outline: "Səkkizbucaqlı daş, sivri taxçalar və radial günbəz",
    },
    "spa-wellness": {
      navLabel: "Spa / Sağlamlıq",
      title: "Spa və sağlamlıq",
      offerings: ["Termal otaqlar", "Sağlamlıq mərkəzləri", "Masaj otaqları"],
      introduction:
        "Müalicə yönümlü interyerlərdən qapalı sağlamlıq hovuzlarına qədər istilik, suya dalma və dincəlmək üçün məkanlar.",
      outline: "Dairəvi dalma hovuzu, oturacaq və prosedur səthi",
    },
    saunas: {
      navLabel: "Saunalar",
      title: "Saunalar",
      offerings: ["Quru saunalar", "Yaş saunalar", "Fin saunaları"],
      introduction:
        "Taxta üzlüklü termal otaqlar pilləli oturacaqlar, qızdırıcılar, daş, şüşə və inteqrasiya olunmuş isti işıqla kompozisiya edilir.",
      outline: "Pilləli L formalı skamyalar, taxta reykalar və qızdırıcı",
    },
    pools: {
      navLabel: "Hovuzlar",
      title: "Hovuzlar",
      offerings: [
        "İsti dalma hovuzu",
        "İlıq dalma hovuzu",
        "Soyuq dalma hovuzu",
        "Qapalı hovuzlar",
        "Açıq hovuzlar",
      ],
      introduction:
        "Qapalı və açıq hovuzlar, dalma hovuzları, inteqrasiya olunmuş spa hovuzları, fəvvarələr və fərdi mozaika səthləri.",
      outline: "Əyri çanaq, balıq pulcuğu formalı kənar və dairəvi fəvvarə",
    },
    systems: {
      navLabel: "Sistemlər",
      title: "Hidravlik sistemlər və nəm məkanların işıqlandırılması",
      offerings: [
        "Suyun dövriyyəsi",
        "Drenaj",
        "Su elementləri",
        "Nəm məkanların işıqlandırılması",
      ],
      introduction:
        "İnteqrasiya olunmuş su dövriyyəsi, drenaj, su elementləri və işıqlandırma həllərinin seçilmiş görünən nəticələri.",
      outline: "Forsunkalar, drenajlar, su sütunu və işıqlandırma nöqtələri",
    },
  },
  projects: {
    "blue-gold-hammam": {
      title: "Mavi və qızılı hamam",
      category: "Türk hamamı",
      description:
        "Son tamamlama mərhələsində olan bu hamam interyeri səkkizbucaqlı damarlı mərmər masa, əyri kobalt mozaikalı oturacaqlar, sivri taxçalar və tünd mavi-qızılı mozaika günbəzi ətrafında qurulub.",
      materials: [
        "Kobalt rəngli şüşə mozaika",
        "Damarlı mərmər",
        "Oyma əhəngdaşı",
        "Pirinç işıqlandırma armaturları",
      ],
      imageAlts: [
        "Hamamda kobalt mozaikalı oturacaq və mavi-qızılı sivri taxça ilə üzbəüz yerləşən səkkizbucaqlı damarlı mərmər masa.",
        "Sivri mozaika taxçası, spiral sütunlar, mavi oturacaqlar və mərmər masanın kənarı görünən simmetrik hamam mənzərəsi.",
        "Oyma daş çərçivəli, işıqlandırılmış mavi, ağ və qızılı taxçanın altındakı əyri kobalt mozaikalı oturacaq.",
        "Firuzəyi mozaika və oyma daş zolaqlarla əhatələnmiş lacivərd-qızılı mozaika hamam günbəzinə aşağıdan baxış.",
      ],
    },
    "blue-mosaic-hammam-study": {
      title: "Mavi mozaikalı hamam araşdırması",
      category: "Şərq hamamı üzrə dizayn araşdırması",
      description:
        "Kobalt mozaikalı oturacaqları, oyma çanaqları, naxışlı tağları, ağ mərmər səthləri və qızılı vurğulu tağtavanı birləşdirən ardıcıl vizuallaşdırma araşdırması.",
      materials: [
        "Kobalt mozaika",
        "Ağ mərmər",
        "Oyma çanaqlar",
        "Pirinç armaturlar",
      ],
      imageAlts: [
        "Əyri oturacaqlar, oyma çanaqlar və naxışlı tağları olan simmetrik mavi mozaikalı hamamın memarlıq vizuallaşdırması.",
        "Dilimli divar pannosu, qoşa mərmər çanaq və damarlı daş masası olan mavi mozaikalı hamamın geniş vizuallaşdırması.",
        "Mavi mozaikalı oturacaqlar, zolaqlı mərmər döşəmə, qatlanmış dəsmallar və qoşa çanaqları olan eyni hamamın yan görünüşü.",
      ],
    },
    "mosaic-wellness-room": {
      title: "Mozaikalı sağlamlıq otağı",
      category: "Qapalı sağlamlıq otağı",
      description:
        "Sənədləşdirilmiş qapalı sağlamlıq məkanında döşəməyə çökdürülmüş dairəvi çanaq, mavi mozaikalı oturacaqlar, daşma barmaqlıqları, mərkəzi fəvvarə borusu və mərmər üstlü prosedur səthi bir araya gəlir.",
      materials: [
        "Mavi şüşə mozaika",
        "Ağ mərmər",
        "Daşma barmaqlıqları",
        "Metal su armaturu",
      ],
      imageAlts: [
        "Dairəvi çanaq, mozaika ilə üzlənmiş oturacaqlar, daşma barmaqlıqları və mərmər üzlü prosedur səthi olan qapalı mavi mozaikalı sağlamlıq otağına yuxarıdan baxış.",
      ],
    },
    "illuminated-timber-sauna": {
      title: "İşıqlandırılmış taxta sauna",
      category: "Taxta sauna",
      description:
        "Pilləli L formalı oturacaqları, tünd həndəsi inkrustasiyaları, qoruyucu çəpərlə əhatələnmiş sobası və skamyaların arxasına inteqrasiya edilmiş isti dolayı işığı olan tamamlanmış taxta üzlüklü sauna.",
      materials: [
        "Açıq rəngli taxta",
        "Tünd taxta inkrustasiya",
        "Reykalı oturacaqlar",
        "İnteqrasiya olunmuş LED işıq",
      ],
      imageAlts: [
        "Həndəsi tünd taxta söykənəcəyi və isti dolayı işıqlandırması olan sauna skamyasının ön görünüşü.",
        "İşıqlandırılmış V formalı panellər, vedrə və taxta çömçəsi olan pilləli L formalı sauna skamyalarının küncdən görünüşü.",
        "Tünd həndəsi inkrustasiya, isti LED zolaqlar və maili başaltısı olan açıq rəngli taxta sauna söykənəcəyinin detalı.",
        "Reykalı skamya, taxta başaltı, tünd söykənəcək zolaqları və əyri işıq sipəri olan sauna küncü.",
      ],
    },
    "pool-after-dark": {
      title: "Gecə işıqlandırılan hovuz",
      category: "Açıq hovuz",
      description:
        "Gündüz və gecə sənədləşdirilmiş düzbucaqlı açıq hovuzda göyümtül sualtı işıq, tünd taxta tonlu döşəmə və kürə formalı lampalar suyun əkslərini formalaşdırır.",
      materials: [
        "Mavi mozaika",
        "Açıq rəngli kənar daşı",
        "Taxta tonlu döşəmə",
        "Sualtı işıqlandırma",
      ],
      imageAlts: [
        "Tünd döşəmə, kürə lampalar, kərpic yaşayış evi və hovuz pavilyonu ilə əhatələnən göyümtül işıqlı düzbucaqlı açıq hovuzun gecə görünüşü.",
        "Kürə lampalar və üstüörtülü terrasla haşiyələnmiş mavi işıqlı düzbucaqlı hovuz boyunca geniş gecə görünüşü.",
        "Ağ haşiyəsi, taxta tonlu döşəməsi və kürə lampaları olan eyni firuzəyi mozaikalı hovuzun gündüz görünüşü.",
      ],
    },
    "fish-scale-mosaic-pool": {
      title: "Balıq pulcuğu naxışlı mozaika hovuzu",
      category: "Açıq hovuz",
      description:
        "Bu əyri açıq hovuzda mavi-ağ balıq pulcuğu naxışlı mozaika çanağın həndəsəsini izləyir; hovuzu yaşıllıqla haşiyələnmiş kənarlar, açıq rəngli haşiyə daşı və paslanmayan polad su elementləri tamamlayır.",
      materials: [
        "Balıq pulcuğu naxışlı mozaika",
        "Açıq rəngli daş",
        "Paslanmayan polad",
        "Yaşıllıq kənarları",
      ],
      imageAlts: [
        "Firuzəyi balıq pulcuğu naxışlı mozaikası, açıq rəngli haşiyə daşı və sərv ağacları olan əyri açıq hovuza yuxarıdan baxış.",
        "Paslanmayan polad nərdivanı, daş döşəməsi, qazonu və palma ağacları olan balıq pulcuğu naxışlı mozaika hovuzunun geniş görünüşü.",
        "Palma əkilmiş adacığın ətrafında əyilən, paslanmayan polad şəlalə elementi olan balıq pulcuğu naxışlı mozaika hovuzu.",
      ],
    },
    "fountain-garden-pool": {
      title: "Fəvvarəli bağ hovuzu",
      category: "Açıq hovuz və fəvvarə",
      description:
        "Sərbəst formalı firuzəyi hovuz üçpilləli oyma daş fəvvarəli dairəvi çanağa uzanır və açıq rəngli döşəmə, qazon, həmişəyaşıl bitkilərlə əhatələnir.",
      materials: [
        "Firuzəyi mozaika",
        "Oyma daş",
        "Açıq rəngli döşəmə",
        "Bağ yaşıllığı",
      ],
      imageAlts: [
        "Dairəvi çanağı, pilləli daş fəvvarəsi, açıq rəngli döşəməsi və qazonu olan sərbəst formalı firuzəyi hovuza yuxarıdan baxış.",
        "Tamamlanmamış döşəmənin ətrafında alətlər və işçilərlə eyni əyri hovuzun və işləyən pilləli fəvvarənin quraşdırma görünüşü.",
      ],
    },
  },
  systems: {
    "underwater-lighting": {
      title: "Sualtı işıqlandırma",
      description:
        "Son tamamlama mərhələsində qapalı hovuz zalında sənədləşdirilmiş sualtı işıq cihazları və göyümtül işıqlandırma.",
      imageAlt:
        "Tamamlama zamanı görünən sualtı işıq cihazları, daşma barmaqlıqları, nərdivan və şüşə divarları olan qapalı hovuz zalı.",
    },
    "pool-fittings-drainage": {
      title: "Hovuz armaturları və drenaj",
      description:
        "Hovuz doldurulmazdan əvvəl qeydə alınmış görünən divar forsunkaları, dib drenajları, haşiyə daşları və döşəmə qoruyucuları.",
      imageAlt:
        "Tamamlama zamanı görünən divar forsunkaları, dib drenajları, haşiyə daşları və bükülmüş su elementi olan boş mavi mozaikalı qapalı hovuz.",
    },
    "water-column-feature": {
      title: "Su sütunu elementi",
      description:
        "Asılı paslanmayan polad sütun mərkəzi su şəlaləsini dairəvi qapalı çanağa yönəldir.",
      imageAlt:
        "Şüşə günbəzin altında, mərkəzdə su axıdan paslanmayan polad sütunu olan, tamamlama mərhələsindəki dairəvi qapalı çanaq.",
    },
    "overflow-water-feature": {
      title: "Daşma sistemi və su elementi",
      description:
        "Açıq hovuzun kənarına inteqrasiya edilmiş perimetr daşma kanalı və paslanmayan polad şəlalə çıxışı.",
      imageAlt:
        "Perimetr daşma kanalı, açıq rəngli daş haşiyəsi və paslanmayan polad şəlalə çıxışı olan oval açıq hovuz.",
    },
  },
} satisfies TranslationDictionary;
