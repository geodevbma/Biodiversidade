import argparse
import json
import random
import struct
import sys
import zlib
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import text

# Garante import local do pacote app quando rodado via "python scripts/..."
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.db.init_db import init_db
from app.db.session import SessionLocal
from app.models.colaborador import ColaboradorCampo
from app.models.registro_fauna import RegistroFauna


SEED_PREFIX = "SEED-FAUNA-BR"
MEDIA_BASE = ROOT / "app" / "media" / "fauna" / "seed"


@dataclass(frozen=True)
class LocalBrasil:
    municipio: str
    uf: str
    latitude: float
    longitude: float


LOCACOES_BRASIL = [
    LocalBrasil("Rio Branco", "AC", -9.97499, -67.82430),
    LocalBrasil("Maceio", "AL", -9.64985, -35.70895),
    LocalBrasil("Macapa", "AP", 0.03493, -51.06942),
    LocalBrasil("Manaus", "AM", -3.11903, -60.02173),
    LocalBrasil("Salvador", "BA", -12.97140, -38.50140),
    LocalBrasil("Fortaleza", "CE", -3.73186, -38.52667),
    LocalBrasil("Brasilia", "DF", -15.79389, -47.88278),
    LocalBrasil("Vitoria", "ES", -20.31550, -40.31280),
    LocalBrasil("Goiania", "GO", -16.68690, -49.26480),
    LocalBrasil("Sao Luis", "MA", -2.53874, -44.28250),
    LocalBrasil("Cuiaba", "MT", -15.60141, -56.09789),
    LocalBrasil("Campo Grande", "MS", -20.46970, -54.62010),
    LocalBrasil("Belo Horizonte", "MG", -19.91670, -43.93450),
    LocalBrasil("Belem", "PA", -1.45583, -48.50389),
    LocalBrasil("Joao Pessoa", "PB", -7.11950, -34.84500),
    LocalBrasil("Curitiba", "PR", -25.42840, -49.27330),
    LocalBrasil("Recife", "PE", -8.05389, -34.88111),
    LocalBrasil("Teresina", "PI", -5.08917, -42.80194),
    LocalBrasil("Rio de Janeiro", "RJ", -22.90680, -43.17290),
    LocalBrasil("Natal", "RN", -5.79448, -35.21100),
    LocalBrasil("Porto Alegre", "RS", -30.03310, -51.23000),
    LocalBrasil("Porto Velho", "RO", -8.76077, -63.89990),
    LocalBrasil("Boa Vista", "RR", 2.82350, -60.67530),
    LocalBrasil("Florianopolis", "SC", -27.59490, -48.54820),
    LocalBrasil("Sao Paulo", "SP", -23.55050, -46.63330),
    LocalBrasil("Aracaju", "SE", -10.94720, -37.07310),
    LocalBrasil("Palmas", "TO", -10.18440, -48.33360),
]


NOMES_COLABORADOR = [
    "Ana Souza",
    "Bruno Lima",
    "Carla Rocha",
    "Diego Oliveira",
    "Elisa Martins",
    "Felipe Santos",
    "Giovana Alves",
    "Henrique Costa",
]

BIOLOGOS = [
    "Dra. Mariana Nunes",
    "Dr. Pedro Ribeiro",
    "Dra. Luiza Campos",
    "Dr. Rafael Moraes",
    "Dra. Camila Prado",
]

ESPECIES = [
    "Cerdocyon thous",
    "Alouatta guariba",
    "Hydrochoerus hydrochaeris",
    "Caiman latirostris",
    "Mazama americana",
    "Didelphis albiventris",
    "Leopardus pardalis",
    "Tapirus terrestris",
    "Tayassu pecari",
    "Ara chloropterus",
]

PERIODOS = ["MANHA", "TARDE", "NOITE", "MADRUGADA"]
ESTADOS_SAUDE = ["ESTAVEL", "FERIDO", "DEBILITADO", "BOM", "OBSERVACAO"]
DESTINOS = ["SOLTURA", "CENTRO_REABILITACAO", "MONITORAMENTO", "UNIDADE_CONSERVACAO"]
STATUS = ["SINCRONIZADO", "VALIDADO", "PENDENTE"]


def _chunk(tag: bytes, data: bytes) -> bytes:
    size = struct.pack(">I", len(data))
    crc = struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    return size + tag + data + crc


def gerar_png_solid(width: int, height: int, rgb: tuple[int, int, int]) -> bytes:
    row = b"\x00" + bytes(rgb) * width
    raw = row * height
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    idat = zlib.compress(raw, level=9)
    return (
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", ihdr)
        + _chunk(b"IDAT", idat)
        + _chunk(b"IEND", b"")
    )


def salvar_imagem(path: Path, rgb: tuple[int, int, int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(gerar_png_solid(320, 240, rgb))


def coordenada_com_jitter(base: float, rng: random.Random, amplitude: float) -> float:
    return round(base + rng.uniform(-amplitude, amplitude), 6)


def garantir_colaboradores(db, minimo: int = 6) -> list[ColaboradorCampo]:
    colaboradores = db.query(ColaboradorCampo).filter(ColaboradorCampo.ativo.is_(True)).all()
    faltantes = max(0, minimo - len(colaboradores))

    for i in range(faltantes):
        nome = NOMES_COLABORADOR[i % len(NOMES_COLABORADOR)]
        slug = nome.lower().replace(" ", ".")
        novo = ColaboradorCampo(
            nome=nome,
            email=f"{slug}{i+1}@teste.local",
            telefone=f"1199999{1000 + i}",
            documento=f"000.000.000-{10 + i:02d}",
            senha_hash=None,
            ativo=True,
        )
        db.add(novo)

    if faltantes:
        db.commit()

    return db.query(ColaboradorCampo).filter(ColaboradorCampo.ativo.is_(True)).all()


def limpar_registros_seed(db) -> int:
    sql = text("DELETE FROM registros_fauna WHERE id_dispositivo LIKE :prefix")
    result = db.execute(sql, {"prefix": f"{SEED_PREFIX}-%"})
    db.commit()
    return int(result.rowcount or 0)


def gerar_registros(
    db,
    qtd: int,
    rng: random.Random,
    colaboradores: list[ColaboradorCampo],
) -> int:
    agora = datetime.now(timezone.utc)
    locais = LOCACOES_BRASIL.copy()
    rng.shuffle(locais)

    registros: list[RegistroFauna] = []
    for i in range(qtd):
        loc = locais[i % len(locais)]
        colaborador = colaboradores[i % len(colaboradores)]

        lat = coordenada_com_jitter(loc.latitude, rng, 0.22)
        lon = coordenada_com_jitter(loc.longitude, rng, 0.22)
        data_captura = agora - timedelta(
            days=rng.randint(1, 180),
            hours=rng.randint(0, 23),
            minutes=rng.randint(0, 59),
        )
        created_at = data_captura + timedelta(minutes=rng.randint(1, 30))
        updated_at = created_at + timedelta(minutes=rng.randint(5, 240))
        gps_manual = rng.random() < 0.28

        registro_tag = f"{i + 1:03d}"
        id_dispositivo = f"{SEED_PREFIX}-{registro_tag}"
        pasta_midia = MEDIA_BASE / id_dispositivo

        animal_rgb = (rng.randint(60, 210), rng.randint(60, 210), rng.randint(60, 210))
        local_rgb = (rng.randint(60, 210), rng.randint(60, 210), rng.randint(60, 210))
        assinatura_rgb = (rng.randint(10, 60), rng.randint(10, 60), rng.randint(10, 60))

        foto_animal_file = pasta_midia / f"animal_{registro_tag}.png"
        foto_local_file = pasta_midia / f"local_{registro_tag}.png"
        assinatura_file = pasta_midia / f"assinatura_{registro_tag}.png"
        salvar_imagem(foto_animal_file, animal_rgb)
        salvar_imagem(foto_local_file, local_rgb)
        salvar_imagem(assinatura_file, assinatura_rgb)

        foto_animal_path = (
            "/media/" + foto_animal_file.relative_to(ROOT / "app" / "media").as_posix()
        )
        foto_local_path = (
            "/media/" + foto_local_file.relative_to(ROOT / "app" / "media").as_posix()
        )
        assinatura_path = (
            "/media/" + assinatura_file.relative_to(ROOT / "app" / "media").as_posix()
        )

        payload = {
            "origem": "seed_script",
            "coleta": {
                "municipio": loc.municipio,
                "uf": loc.uf,
                "gps_manual": gps_manual,
            },
            "equipamento": {
                "id_dispositivo": id_dispositivo,
                "bateria_percentual": rng.randint(35, 99),
            },
        }

        reg = RegistroFauna(
            id_dispositivo=id_dispositivo,
            colaborador_id=colaborador.id,
            created_at=created_at,
            updated_at=updated_at,
            data_captura=data_captura,
            animal_number=f"ANM-{1000 + i}",
            nome_cientifico=ESPECIES[i % len(ESPECIES)],
            biologo_responsavel=BIOLOGOS[i % len(BIOLOGOS)],
            gps_manual=gps_manual,
            latitude=lat,
            longitude=lon,
            gps_accuracy=round(rng.uniform(2.5, 14.8), 2),
            gps_timestamp=data_captura + timedelta(minutes=1),
            manual_latitude=f"{lat:.6f}" if gps_manual else None,
            manual_longitude=f"{lon:.6f}" if gps_manual else None,
            municipio=f"{loc.municipio}/{loc.uf}",
            local_captura=f"Area de monitoramento {loc.uf}-{(i % 7) + 1}",
            periodo_resgate=PERIODOS[i % len(PERIODOS)],
            estado_saude=ESTADOS_SAUDE[i % len(ESTADOS_SAUDE)],
            destino=DESTINOS[i % len(DESTINOS)],
            observacoes=(
                f"Registro ficticio {i + 1} para testes de listagem, mapa, exportacao e fotos."
            ),
            foto_animal_path=foto_animal_path,
            foto_local_path=foto_local_path,
            assinatura_usuario=assinatura_path,
            payload_json=json.dumps(payload, ensure_ascii=False),
            status=STATUS[i % len(STATUS)],
        )
        registros.append(reg)

    db.add_all(registros)
    db.commit()
    return len(registros)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Insere registros ficticios completos em registros_fauna."
    )
    parser.add_argument(
        "--qtd",
        type=int,
        default=50,
        help="Quantidade de registros ficticios a inserir (default: 50).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=20260212,
        help="Seed do gerador aleatorio para dados reprodutiveis.",
    )
    parser.add_argument(
        "--nao-limpar",
        action="store_true",
        help=(
            "Nao remove registros anteriores com prefixo de seed. "
            "Sem esta flag, o script limpa os seeds anteriores."
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.qtd < 1:
        print("ERRO: --qtd deve ser maior que zero.")
        return 1

    init_db()
    rng = random.Random(args.seed)

    db = SessionLocal()
    try:
        if not args.nao_limpar:
            removidos = limpar_registros_seed(db)
            print(f"OK: removidos {removidos} registros seed anteriores.")

        colaboradores = garantir_colaboradores(db, minimo=6)
        inseridos = gerar_registros(db=db, qtd=args.qtd, rng=rng, colaboradores=colaboradores)

        print(f"OK: inseridos {inseridos} registros ficticios em registros_fauna.")
        print(f"OK: fotos em {MEDIA_BASE}")
        print("OK: distribuicao geografica abrangendo todas as regioes do Brasil.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
