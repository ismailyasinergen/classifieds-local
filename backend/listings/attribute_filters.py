from urllib.parse import urlencode


ATTRIBUTE_FILTERS_BY_CATEGORY = {
    "cars": [
        {"key": "marka", "label": "Brand", "placeholder": "BMW, Toyota..."},
        {"key": "model", "label": "Model", "placeholder": "520i, Corolla..."},
        {"key": "yil", "label": "Year", "placeholder": "2018"},
        {"key": "km", "label": "Mileage", "placeholder": "150000"},
        {"key": "yakit_tipi", "label": "Fuel", "placeholder": "Diesel, Petrol..."},
        {"key": "vites", "label": "Transmission", "placeholder": "Automatic..."},
    ],
    "motorcycles": [
        {"key": "marka", "label": "Brand", "placeholder": "Honda, Yamaha..."},
        {"key": "model", "label": "Model", "placeholder": "CBR..."},
        {"key": "yil", "label": "Year", "placeholder": "2020"},
        {"key": "km", "label": "Mileage", "placeholder": "25000"},
    ],
    "commercial-vehicles": [
        {"key": "arac_tipi", "label": "Vehicle type", "placeholder": "Panelvan..."},
        {"key": "marka", "label": "Brand", "placeholder": "Ford..."},
        {"key": "model", "label": "Model", "placeholder": "Transit..."},
        {"key": "yil", "label": "Year", "placeholder": "2019"},
        {"key": "km", "label": "Mileage", "placeholder": "120000"},
    ],
    "homes-for-sale": [
        {"key": "oda_sayisi", "label": "Rooms", "placeholder": "2+1"},
        {"key": "m2_brut", "label": "Gross m²", "placeholder": "120"},
        {"key": "m2_net", "label": "Net m²", "placeholder": "95"},
        {"key": "bina_yasi", "label": "Building age", "placeholder": "5"},
        {"key": "bulundugu_kat", "label": "Floor", "placeholder": "3"},
    ],
    "homes-for-rent": [
        {"key": "oda_sayisi", "label": "Rooms", "placeholder": "2+1"},
        {"key": "m2_brut", "label": "Gross m²", "placeholder": "120"},
        {"key": "m2_net", "label": "Net m²", "placeholder": "95"},
        {"key": "bina_yasi", "label": "Building age", "placeholder": "5"},
        {"key": "bulundugu_kat", "label": "Floor", "placeholder": "3"},
    ],
    "land": [
        {"key": "m2", "label": "m²", "placeholder": "500"},
        {"key": "imar_durumu", "label": "Zoning", "placeholder": "Residential..."},
        {"key": "ada_no", "label": "Block no", "placeholder": "123"},
        {"key": "parsel_no", "label": "Parcel no", "placeholder": "45"},
    ],
    "phones": [
        {"key": "marka", "label": "Brand", "placeholder": "Apple, Samsung..."},
        {"key": "model", "label": "Model", "placeholder": "iPhone 14..."},
        {"key": "kapasite", "label": "Capacity", "placeholder": "128 GB"},
        {"key": "renk", "label": "Color", "placeholder": "Black"},
        {"key": "durum", "label": "Condition", "placeholder": "Used..."},
    ],
    "computers": [
        {"key": "marka", "label": "Brand", "placeholder": "Apple, Lenovo..."},
        {"key": "model", "label": "Model", "placeholder": "MacBook Pro..."},
        {"key": "islemci", "label": "CPU", "placeholder": "Intel i7..."},
        {"key": "ram", "label": "RAM", "placeholder": "16 GB"},
        {"key": "ssd", "label": "SSD", "placeholder": "512 GB"},
    ],
    "cameras": [
        {"key": "marka", "label": "Brand", "placeholder": "Canon, Sony..."},
        {"key": "model", "label": "Model", "placeholder": "EOS R6..."},
        {"key": "lens", "label": "Lens", "placeholder": "24-70mm"},
        {"key": "video", "label": "Video", "placeholder": "4K"},
    ],
    "furniture": [
        {"key": "urun_tipi", "label": "Product type", "placeholder": "Sofa set..."},
        {"key": "marka", "label": "Brand", "placeholder": "Bellona..."},
        {"key": "malzeme", "label": "Material", "placeholder": "Wood..."},
        {"key": "renk", "label": "Color", "placeholder": "Gray"},
        {"key": "durum", "label": "Condition", "placeholder": "Used..."},
    ],
    "appliances": [
        {"key": "urun_tipi", "label": "Product type", "placeholder": "Fridge..."},
        {"key": "marka", "label": "Brand", "placeholder": "Bosch..."},
        {"key": "model", "label": "Model", "placeholder": "No Frost..."},
        {"key": "kapasite", "label": "Capacity", "placeholder": "500 lt"},
        {"key": "durum", "label": "Condition", "placeholder": "Used..."},
    ],
}


def normalize_category_slug(category_slug):
    return (category_slug or "").strip()


def get_attribute_filter_specs(category_slug):
    return list(ATTRIBUTE_FILTERS_BY_CATEGORY.get(normalize_category_slug(category_slug), []))



def get_attribute_filter_specs_by_category():
    result = {}
    for category_slug, specs in ATTRIBUTE_FILTERS_BY_CATEGORY.items():
        result[category_slug] = [
            {
                **spec,
                "param": "attr_" + spec["key"],
            }
            for spec in specs
        ]
    return result


def get_attribute_filter_context(request, category_slug):
    fields = []
    for spec in get_attribute_filter_specs(category_slug):
        param = "attr_" + spec["key"]
        fields.append({
            **spec,
            "param": param,
            "value": request.GET.get(param, "").strip(),
        })

    return {
        "attribute_filter_category_slug": normalize_category_slug(category_slug),
        "attribute_filter_fields": fields,
        "attribute_filter_specs_by_category": get_attribute_filter_specs_by_category(),
    }


def apply_attribute_filters(queryset, request, category_slug):
    for spec in get_attribute_filter_specs(category_slug):
        value = request.GET.get("attr_" + spec["key"], "").strip()
        if not value:
            continue

        queryset = queryset.filter(**{
            f"attributes__{spec["key"]}__icontains": value,
        })

    return queryset


def get_page_querystring(request):
    params = request.GET.copy()
    params.pop("page", None)
    return params.urlencode()


# REAL_ESTATE_ATTRIBUTE_FILTERS_V67
REAL_ESTATE_ATTRIBUTE_FILTERS_V67 = [
    {"key": "m2_brut", "label": "m² (Brüt)", "placeholder": "120"},
    {"key": "m2_net", "label": "m² (Net)", "placeholder": "95"},
    {"key": "acik_alan_m2", "label": "Açık Alan m²", "placeholder": "25"},
    {"key": "oda_sayisi", "label": "Oda Sayısı", "placeholder": "3+1"},
    {"key": "bina_yasi", "label": "Bina Yaşı", "placeholder": "5-10 arası"},
    {"key": "bulundugu_kat", "label": "Bulunduğu Kat", "placeholder": "3"},
    {"key": "kat_sayisi", "label": "Kat Sayısı", "placeholder": "8"},
    {"key": "isitma", "label": "Isıtma", "placeholder": "Kombi"},
    {"key": "banyo_sayisi", "label": "Banyo Sayısı", "placeholder": "2"},
    {"key": "mutfak", "label": "Mutfak", "placeholder": "Açık / Kapalı"},
    {"key": "balkon", "label": "Balkon", "placeholder": "Evet / Hayır"},
    {"key": "asansor", "label": "Asansör", "placeholder": "Evet / Hayır"},
    {"key": "otopark", "label": "Otopark", "placeholder": "Açık / Kapalı"},
    {"key": "esyali", "label": "Eşyalı", "placeholder": "Evet / Hayır"},
    {"key": "kullanim_durumu", "label": "Kullanım Durumu", "placeholder": "Boş / Kiracılı"},
    {"key": "site_i_cerisinde", "label": "Site İçerisinde", "placeholder": "Evet / Hayır"},
    {"key": "krediye_uygun", "label": "Krediye Uygun", "placeholder": "Evet / Hayır"},
    {"key": "tapu_durumu", "label": "Tapu Durumu", "placeholder": "Kat Mülkiyetli"},
    {"key": "kimden", "label": "Kimden", "placeholder": "Sahibinden"},
    {"key": "takas", "label": "Takaslı", "placeholder": "Evet / Hayır"},
    {"key": "foto_video", "label": "Fotoğraf / Video", "placeholder": "Fotoğraflı"},
    {"key": "harita", "label": "Harita", "placeholder": "Evet / Hayır"},
]

for _real_estate_slug in ("homes-for-sale", "homes-for-rent"):
    ATTRIBUTE_FILTERS_BY_CATEGORY[_real_estate_slug] = REAL_ESTATE_ATTRIBUTE_FILTERS_V67
