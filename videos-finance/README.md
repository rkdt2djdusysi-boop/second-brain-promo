# Vidéos finance (@MTM)

Vidéos animées minimalistes noir et blanc, contenu en anglais.

| Vidéo | Format | Durée | Voix |
|---|---|---|---|
| `video_penny.mp4` — $1M now or 1 penny doubled for 30 days? | TikTok 1080×1920 | 30 s | à ajouter |
| `video_100m_offers.mp4` — résumé de *$100M Offers* | TikTok 720×1280 | 49 s | oui |
| `video_mistake.mp4` — Stop Making This Mistake | TikTok 720×1280 | 26 s | oui |
| `video_rich_dad_poor_dad.mp4` — résumé de *Rich Dad Poor Dad* | YouTube 1920×1080 | 78 s | à ajouter |

`couverture_penny.png` : image de couverture pour la vidéo penny.

## Refaire une vidéo

1. Installer Python (cocher « Add Python to PATH »), puis `pip install pillow numpy` et `winget install ffmpeg`.
2. Mettre le script (dossier `scripts/`) et sa voix ElevenLabs dans le même dossier :
   - `generer_video.py` → `voix.mp3`
   - `generer_video_100m.py` → `voix_100m.mp3`
   - `generer_video_rich_dad.py` → `voix_rich_dad.mp3`
   - `generer_video_penny.py` → `voix_penny.mp3`
3. Ouvrir le dossier, taper `cmd` dans la barre d'adresse, puis `python nom_du_script.py`.
