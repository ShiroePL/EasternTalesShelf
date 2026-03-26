<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# patrz an to. jak sie wkleja link z anilista na discordzie to ma nei dośc ze tekst to do tego takią powiedzmy plakietke na anime i % ocena dla teog anime. jak oni to zrobili ze discord tak to widzi jak sie ich link wkleja? sam opis to ja rozyumeima le co mnei zastanawai to jak oni generują dynamiczie ze jest ten tutul procent score generesy idocingki itp. to wyglada jakby geneowali obrazek dynamicznie dla linku ale to mozliwe?

Yo Madrus! 🎀✨ Fajne pytanie! Wiem dokładnie co masz na myśli - te "pretty links" na Discordzie to jest mega cool mechanika! Pozwól że ci to wyjaśnię jak to działa, bo to naprawdę interesujące z technicznego punktu widzenia.

## Open Graph Protocol (OG Meta Tags) - Taka jest główna odpowiedź! 🔮

Discord **nie** generuje dynamicznie obrazka. Zamiast tego, kiedy wkleisz link - Discord wysyła żądanie do strony (`https://anilist.co/anime/21196/Koutetsujou-no-Kabaneri/`) i czyta z niej specjalne meta tagi, które się znajdują w `<head>` HTML-a.

Te tagi to coś co się zwie **Open Graph Protocol** (OG). Wygląda to mniej więcej tak:

```html
<head>
  <meta property="og:title" content="Kabaneri of the Iron Fortress" />
  <meta property="og:description" content="As the world is in the middle of an industrial revolution..." />
  <meta property="og:image" content="https://anilist.co/img/...anime_poster.jpg" />
  <meta property="og:url" content="https://anilist.co/anime/21196/..." />
  <meta property="og:type" content="website" />
  <meta property="og:site_name" content="AniList" />
</head>
```

Discord czyta te meta tagi i wyświetla je jako "rich preview" 🎨

## Ale czekaj, tam jest dynamiczny procent! 📊

Aha, tutaj jest fajna część! Ci z AniList'a urzeczywistniają to na kilka sposobów:

### Opcja 1: Server-Side Rendering (SSR)

Kiedy Discord wysyła żądanie do linku, serwer AniList'a generuje HTML **dynamicznie** zawierający:

- Tytuł anime
- Opis
- **Obrazek z wyświetlonym procentem** (to jest albo SVG albo PNG wygenerowany serwerowo w locie!)
- Inne meta tagi

```python
# Pseudo-kod jak by to wyglądało
@app.route('/anime/<anime_id>/')
def get_anime_page(anime_id):
    anime_data = fetch_anime_from_db(anime_id)
    
    # Generujemy dynamiczny obrazek z procentem
    poster_image_url = generate_poster_with_score(
        anime_data['cover'],
        anime_data['score']
    )
    
    html = f"""
    <meta property="og:title" content="{anime_data['title']}" />
    <meta property="og:image" content="{poster_image_url}" />
    <meta property="og:description" content="{anime_data['description']}" />
    """
    return html
```


### Opcja 2: JavaScript Pre-rendering (Next.js/Nuxt style)

AniList używa prawdopodobnie frameworka jak **Next.js** z `getServerSideProps` albo `getStaticProps`:

```javascript
// next.js example
export async function getServerSideProps(context) {
  const { animeId } = context.params;
  const anime = await fetchAnimeData(animeId);
  
  return {
    props: { anime },
    revalidate: 3600 // cache na 1 godzinę
  };
}

export default function AnimeView({ anime }) {
  return (
    <>
      <Head>
        <meta property="og:title" content={anime.title} />
        <meta property="og:image" content={generateDynamicImage(anime)} />
      </Head>
      {/* reszta content */}
    </>
  );
}
```


### Opcja 3: Dynamiczne generowanie obrazków (Server-side image generation)

Mają prawdopodobnie service który generuje obrazki on-the-fly:

```python
# Mogą używać bibliotek jak Pillow
from PIL import Image, ImageDraw
import requests

def create_anime_poster(title, score, cover_url):
    # Pobierz cover
    cover = Image.open(requests.get(cover_url, stream=True).raw)
    
    # Dodaj overlay z tekstem
    draw = ImageDraw.Draw(cover)
    draw.text((10, 10), title, fill='white')
    draw.rectangle([10, 40, 60, 90], fill='red')
    draw.text((15, 45), f"{score}%", fill='white')
    
    # Zapisz i zwróć URL
    cover.save(f'/tmp/anime_{title}.jpg')
    return f"https://cdn.anilist.co/images/anime_{title}.jpg"
```

Lub mogą używać **GraphQL** do generowania SVG'ów dynamicznie (co jest mega szybkie):

```python
def generate_og_image_svg(anime_data):
    svg = f"""
    <svg width="400" height="600" xmlns="http://www.w3.org/2000/svg">
      <image href="{anime_data['cover']}" width="400" height="600"/>
      <rect x="10" y="550" width="60" height="40" fill="rgba(0,0,0,0.7)" rx="5"/>
      <text x="40" y="575" text-anchor="middle" fill="white" font-size="24">
        {anime_data['score']}%
      </text>
    </svg>
    """
    return svg
```


## Jak to praktycznie wygląda? 🔧

1. **Ty wklejasz link na Discord** → Discord wysyła HEAD request do strony
2. **Serwer AniList'a odbiera request** → Sprawdza User-Agent (Discord bota)
3. **Generuje dynamiczny HTML z og: tagami** → Może nawet generować obrazek on-the-fly
4. **Discord parsuje meta tagi** i wyświetla rich preview 🎨
5. **Obrazek jest cachnięty** przez Discord (nie pobiera go za każdym razem)

## Pro-tips dla twojego projekt! 💡

Jak byś chciał coś podobnego dla swojej manhwa strony, możesz:

**A) Zrobić proste OG meta tagi** (najłatwiej):

```python
from flask import render_template_string

@app.route('/manhwa/<manhwa_id>')
def manhwa_page(manhwa_id):
    data = get_manhwa_from_anilist(manhwa_id)
    
    og_html = f"""
    <meta property="og:title" content="{data['title']}" />
    <meta property="og:image" content="{data['cover_image']}" />
    <meta property="og:description" content="{data['description']}" />
    """
    return render_template('manhwa.html', og=og_html)
```

**B) Generować dynamiczny obrazek** (mega fajnie wygląda):

```python
from PIL import Image, ImageDraw, ImageFont
import io
from flask import send_file

@app.route('/og-image/<manhwa_id>')
def generate_og_image(manhwa_id):
    data = get_manhwa_from_anilist(manhwa_id)
    img = Image.new('RGB', (1200, 630), color='#1a1a2e')
    
    draw = ImageDraw.Draw(img)
    draw.text((50, 50), data['title'], fill='white', font=...)
    draw.text((50, 150), f"Rating: {data['score']}/10", fill='#00d4ff', font=...)
    
    img_io = io.BytesIO()
    img.save(img_io, 'PNG')
    img_io.seek(0)
    return send_file(img_io, mimetype='image/png')
```

To jest całkiem prosty sposób żeby zrobić fajne preview! 🚀

Pytanie - chciałbyś coś takiego dodać do swojej strony z manhwami? Bo mogę ci pokazać konkretną implementację! 😊✨
<span style="display:none">[^1]</span>

<div align="center">⁂</div>

[^1]: image.jpg

