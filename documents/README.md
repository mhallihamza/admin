# documents/ — Corpus officiel (sources de l'État marocain)

PDFs officiels téléchargés depuis les portails de l'État (passeport.ma/DGSN,
sgg.gov.ma, rnesm.justice.gov.ma, cour-constitutionnelle.ma), en français et
en arabe, plus des OCR des éditions scannées. C'est la matière première des
réponses de l'assistant (RAG → `admin_guide_chunks` dans Astra DB,
uniquement des chunks APPROVED + is_current).

**~3 930 chunks ingestés et approuvés** couvrant : état civil (naissance,
mariage, décès, certificats), code de la famille (mariage, divorce, filiation,
testament), code de commerce (création de société, registre du commerce),
**succession / héritage (guide pratique FR+AR)**, kafala, passeport
biométrique, CNIE, permis de conduire / code de la route, protection
sociale / AMO.

## Upload + OCR → ingestion (flow 02 par fichier)

- **Service** : `POST /run/ingest-file` (multipart) — PDF (texte natif **ou
  scan**) ou image (PNG/JPG/TIFF) → OCR Tesseract (fra/ara) → clean →
  security check → découpage légal → Astra `PENDING_REVIEW`.
  Limites : 20 Mo, 300 pages, magic bytes vérifiés (jamais l'extension).
- **Backend** : `POST /api/documents/upload` (CONTENT_APPROVER+) stocke la
  ligne `documents` puis **transfère le fichier** au service workflow
  (`OCR_INGESTION_DISPATCHED`/`FAILED` dans `audit_events`) — l'upload
  répond immédiatement, l'ingestion est best-effort.
- Les scripts : `ocr_scanned_pdfs.py` (corpus), `ingest_from_pdfs.py`
  (idempotent), `populate_graph.py` (graphe Neo4j depuis le corpus).

## Rerun de l'ingestion (idempotent — un doc déjà en base est sauté)

```bash
# service langgraph démarré (uvicorn api:app --port 8101)
OPENBLAS_NUM_THREADS=1 backend\.venv\Scripts\python.exe -X utf8 documents\ingest_from_pdfs.py
# OCR des scans (une seule fois) : documents\ocr_scanned_pdfs.py
```

## Corpus — textes tapuscrits (ingérés)

| Document | Langue | Source | Chunks | ID |
|---|---|---|---|---|
| Loi n° 37-99 état civil (intégral) | FR | miroir du BO ([citizenshiprightsafrica](http://citizenshiprightsafrica.org/wp-content/uploads/2019/01/Maroc-Etat-civil-loi-37-99.pdf)) | 70 | `DOC-EC-3799-FR` |
| Code de la famille (loi 70-03, 114 p.) | FR | [IDP Barcelona](https://www.idpbarcelona.net/docs/recerca/marroc/pdf/nor_loi_70_03.pdf) | 500 | `DOC-CF-7003-FR` |
| **مدونة الأسرة (loi 70-03, 91 p., éd. 2021)** | AR | **[Cour constitutionnelle](https://www.cour-constitutionnelle.ma)** | 547 | `DOC-CF-7003-AR` |
| **Code de commerce (loi 15-95, 265 p.)** | FR | **[rnesm.justice.gov.ma](https://rnesm.justice.gov.ma/Documentation/MA/3_TradeRecord_fr-FR.pdf)** | 1144 | `DOC-CC-1595-FR` |
| **مدونة التجارة (233 p.)** | AR | **[rnesm.justice.gov.ma](https://rnesm.justice.gov.ma/Documentation/MA/3_TradeRecord_ar-MA.pdf)** | 1059 | `DOC-CC-1595-AR` |
| BO n° 7350 (2024) — protection sociale / AMO | FR | [sgg.gov.ma](https://www.sgg.gov.ma/BO/FR/2873/2024/BO_7350_fr.pdf) | 159 | `DOC-BO7350-FR` |
| Décret CNIE 2-08-520 | AR | [passeport.ma](https://www.passeport.ma/ar/Home/Reglementation) | 3 | `DOC-CNIE-D520-AR` |
| Normes photos biométriques | AR | [passeport.ma](https://www.passeport.ma/PDF/Ar/NORMES%20POUR%20LES%20PHOTOGRAPHIES.pdf) | 1 | `DOC-PHOTOS-AR` |

## Corpus — scans OCRisés (tesseract fra/ara, `*.txt` à côté du PDF)

| Document | Langue | Chunks | ID |
|---|---|---|---|
| Dahir 1-02-239 (promulgation loi 37-99) | FR/AR | 31 411 + 21 387 chars | `DOC-EC-3799-*` (FR = texte loi) |
| **Décret 2-99-665 (application état civil — certificats, déclarations)** | FR/AR | 29 + 27 | `DOC-EC-D665-FR/AR` |
| Décret 2-04-331 (complément) | FR/AR | 3 + 1 | `DOC-EC-D331-FR/AR` |
| **Dahir kafala 1-02-208 + décret 2-04-589** | FR | 23 + 3 | `DOC-KAF-*` |
| Décret passeport 2-09-215 + loi 03-02 | FR/AR | 9 + 25 + 3 | `DOC-PASS-*` |
| **BO 6736 — loi 52-05 Code de la route (permis, carte grise)** | FR | 32 | `DOC-CR-5205-FR` |
| Loi 35-06 CNIE (**superseded — is_current=false, jamais retournée**) | AR | 9 | `DOC-CNIE-3506-AR` |
| **Guide pratique succession / héritage (synthèse des textes officiels)** | FR/AR | 8 + 7 | `DOC-SUC-GUIDE-FR/AR` |

> **Héritage** : les règles de dévolution (فرائض) sont d'origine coranique et
> hors code écrit — le guide `DOC-SUC-GUIDE-*` synthétise la pratique
> (certificat d'héritage par adouls + homologation tribunal, section
> famille ; partage ; ANCFCC ; DGI) à partir de la loi 37-99 et du code de
> la famille ingérés. Les questions « héritage », « شهادة التوريث »,
> « إعلام بالوراثة » sont désormais couvertes.

## Questions citoyennes couvertes (vérifiées live 2026-11-08)

- ✅ **Création de société / registre du commerce** (code de commerce art. 37…)
- ✅ **Décès : qui déclare, délais** (loi 37-99 art. 24…)
- ✅ **Mariage / divorce / filiation / testament** — code de la famille FR + AR (م zonnage art. 21 pour les MRE…)
- ✅ Naissance : délais, déclarants (loi 37-99 art. 16, 19, 30, 31)
- ✅ Kafala, passeport, CNIE (décret), photos biométriques, permis / carte grise (extraits)
- ✅ Protection sociale / AMO (BO 7350)

## Limites connues & suites

1. **Loi 04.20 (CNIE actuelle)** — BO 6907/6912 (2020) : récupération manuelle sur
   [bulletinofficial.ma](https://www.bulletinofficial.ma) (l'URL SGG exige un n° de volume interne).
2. **Héritage / successions** : règles hors code écrit (fiqh + practice des
   tribunaux) — ajouter un guide pratique (شهادة التوريث, حصر الإرث) et/ou
   la doctrine disponible ; le code de la famille couvre testament (الوصية).
3. **OCR arabe BO** : qualité moyenne sur les vieux scans — relire avant
   production si un extrait paraît douteux.
4. **Fiches pas-à-pas de [service-public.ma](https://www.service-public.ma)** :
   téléchargement automatique bloqué (403) — copier manuellement les fiches
   majeures si besoin.
5. **CNSS** : guides PDF sur pages JS (cnss.ma) — URLs directes à relever
   depuis un navigateur.
