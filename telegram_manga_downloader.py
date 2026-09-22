import asyncio
import re
import shutil
from pathlib import Path

from telethon import TelegramClient


# ============================================================
# CONFIGURAÇÕES
# ============================================================

API_ID = 12345678
API_HASH = "SEU_API_HASH"

GROUP = "@nome_do_grupo"

TEMP_DIR = Path(
    r"C:\Users\junio\Downloads\telegram_mangas_temp"
)

DOWNLOAD_DIR = Path(
    r"F:\Mangas"
)

EXTENSIONS = {
    ".epub",
    ".mobi",
    ".pdf",
    ".cbz",
    ".cbr",
    ".zip",
}

MAX_DOWNLOADS = 4

SSD_RESERVE_GB = 5
CARD_RESERVE_MB = 500


# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def sanitize_name(name: str) -> str:
    return re.sub(
        r'[<>:"/\\|?*]',
        "",
        name,
    ).strip()


def get_manga_name(file_name: str) -> str:
    stem = Path(file_name).stem

    patterns = [
        r"(.+?)\s*[-–]?\s*Vol\.?\s*\d+",
        r"(.+?)\s*[-–]?\s*Volume\s*\d+",
        r"(.+?)\s*[-–]?\s*v\s*\d+",
    ]

    for pattern in patterns:
        match = re.match(
            pattern,
            stem,
            re.IGNORECASE,
        )

        if match:
            return sanitize_name(
                match.group(1)
            )

    return "Outros"


def format_size(size: int) -> str:
    mb = size / (1024 * 1024)

    if mb >= 1024:
        return f"{mb / 1024:.2f} GB"

    return f"{mb:.1f} MB"


def get_free_space(path: Path) -> int:
    return shutil.disk_usage(
        path.anchor
    ).free


def file_is_complete(
    path: Path,
    expected_size: int,
) -> bool:

    if not path.exists():
        return False

    if expected_size <= 0:
        return True

    return (
        path.stat().st_size
        == expected_size
    )


def check_drives() -> None:

    if not Path(
        TEMP_DIR.anchor
    ).exists():

        raise RuntimeError(
            "SSD não disponível."
        )

    if not Path(
        DOWNLOAD_DIR.anchor
    ).exists():

        raise RuntimeError(
            "Cartão de memória não encontrado."
        )


# ============================================================
# CONTROLE DE ESPAÇO
# ============================================================

async def wait_for_ssd_space(
    file_size: int,
) -> None:

    reserve = (
        SSD_RESERVE_GB
        * 1024
        * 1024
        * 1024
    )

    needed = (
        file_size
        + reserve
    )

    while True:

        free = get_free_space(
            TEMP_DIR
        )

        if free >= needed:
            return

        print()
        print(
            "[SSD] Pouco espaço."
        )

        print(
            f"Livre: {format_size(free)}"
        )

        print(
            "Aguardando arquivos serem "
            "copiados para o cartão..."
        )

        await asyncio.sleep(5)


async def wait_for_card_space(
    file_size: int,
) -> None:

    reserve = (
        CARD_RESERVE_MB
        * 1024
        * 1024
    )

    needed = (
        file_size
        + reserve
    )

    while True:

        free = get_free_space(
            DOWNLOAD_DIR
        )

        if free >= needed:
            return

        print()
        print(
            "[CARTÃO] Sem espaço suficiente."
        )

        print(
            f"Livre: {format_size(free)}"
        )

        await asyncio.sleep(10)


# ============================================================
# VELOCIDADE GLOBAL
# ============================================================

active_downloads = {}
speed_lock = asyncio.Lock()


async def update_download_status(
    file_name: str,
    current: int,
    total: int,
) -> None:

    async with speed_lock:

        active_downloads[
            file_name
        ] = (
            current,
            total,
        )


async def remove_download_status(
    file_name: str,
) -> None:

    async with speed_lock:

        active_downloads.pop(
            file_name,
            None,
        )


async def status_worker() -> None:

    previous_total = 0
    previous_time = (
        asyncio.get_running_loop().time()
    )

    while True:

        await asyncio.sleep(1)

        async with speed_lock:

            snapshot = dict(
                active_downloads
            )

        if not snapshot:
            previous_total = 0
            previous_time = (
                asyncio.get_running_loop().time()
            )
            continue

        total_now = sum(
            current
            for current, total
            in snapshot.values()
        )

        now = (
            asyncio.get_running_loop().time()
        )

        delta_bytes = (
            total_now
            - previous_total
        )

        delta_time = (
            now
            - previous_time
        )

        speed = 0

        if (
            previous_total > 0
            and delta_time > 0
        ):

            speed = (
                delta_bytes
                / delta_time
            )

        speed_mb = (
            speed
            / 1024
            / 1024
        )

        print()
        print(
            "================================"
        )

        print(
            f"Downloads ativos: "
            f"{len(snapshot)}"
        )

        print(
            f"Velocidade total: "
            f"{speed_mb:.2f} MB/s"
        )

        for (
            file_name,
            (
                current,
                total,
            ),
        ) in snapshot.items():

            percent = 0

            if total > 0:
                percent = (
                    current
                    / total
                    * 100
                )

            print(
                f"{percent:5.1f}% "
                f"{file_name}"
            )

        print(
            "================================"
        )

        previous_total = (
            total_now
        )

        previous_time = now


# ============================================================
# CALLBACK DO TELETHON
# ============================================================

def create_progress_callback(
    file_name: str,
):

    loop = (
        asyncio.get_running_loop()
    )

    def progress(
        current: int,
        total: int,
    ) -> None:

        asyncio.run_coroutine_threadsafe(
            update_download_status(
                file_name,
                current,
                total,
            ),
            loop,
        )

    return progress


# ============================================================
# CÓPIA SSD -> CARTÃO
# ============================================================

def copy_file(
    source: Path,
    destination: Path,
    expected_size: int,
) -> None:

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temp_destination = (
        destination.parent
        / (
            destination.name
            + ".copying"
        )
    )

    print(
        f"[COPIANDO] "
        f"{destination.name}"
    )

    shutil.copy2(
        source,
        temp_destination,
    )

    copied_size = (
        temp_destination.stat().st_size
    )

    if (
        expected_size > 0
        and copied_size
        != expected_size
    ):

        temp_destination.unlink(
            missing_ok=True
        )

        raise RuntimeError(
            "Tamanho incorreto "
            "após a cópia."
        )

    if destination.exists():

        destination.unlink()

    temp_destination.rename(
        destination
    )

    source.unlink(
        missing_ok=True
    )

    print(
        f"[COPIADO] "
        f"{destination.name}"
    )


async def copy_worker(
    queue: asyncio.Queue,
) -> None:

    while True:

        item = await queue.get()

        if item is None:

            queue.task_done()
            break

        (
            source,
            destination,
            expected_size,
        ) = item

        try:

            await wait_for_card_space(
                expected_size
            )

            await asyncio.to_thread(
                copy_file,
                source,
                destination,
                expected_size,
            )

        except Exception as error:

            print()
            print(
                "[ERRO NA CÓPIA]"
            )

            print(error)

            print(
                "Arquivo mantido no SSD."
            )

        finally:

            queue.task_done()


# ============================================================
# DOWNLOAD DE UM ARQUIVO
# ============================================================

async def download_file(
    semaphore: asyncio.Semaphore,
    message,
    copy_queue: asyncio.Queue,
) -> None:

    async with semaphore:

        file_name = (
            message.file.name
        )

        expected_size = (
            message.file.size
            or 0
        )

        extension = Path(
            file_name
        ).suffix.lower()

        if extension not in EXTENSIONS:
            return

        manga_name = get_manga_name(
            file_name
        )

        safe_file_name = sanitize_name(
            file_name
        )

        destination = (
            DOWNLOAD_DIR
            / manga_name
            / safe_file_name
        )

        # Já existe completo no cartão
        if file_is_complete(
            destination,
            expected_size,
        ):

            print(
                f"[JÁ EXISTE] "
                f"{manga_name} / "
                f"{safe_file_name}"
            )

            return

        temp_folder = (
            TEMP_DIR
            / manga_name
        )

        temp_folder.mkdir(
            parents=True,
            exist_ok=True,
        )

        temp_file = (
            temp_folder
            / safe_file_name
        )

        # Já existe completo no SSD
        if file_is_complete(
            temp_file,
            expected_size,
        ):

            print(
                f"[SSD] Já baixado: "
                f"{safe_file_name}"
            )

            await copy_queue.put(
                (
                    temp_file,
                    destination,
                    expected_size,
                )
            )

            return

        if temp_file.exists():

            temp_file.unlink()

        await wait_for_ssd_space(
            expected_size
        )

        await wait_for_card_space(
            expected_size
        )

        print()
        print(
            f"[BAIXANDO] "
            f"{manga_name}"
        )

        print(
            f"Arquivo: "
            f"{safe_file_name}"
        )

        print(
            f"Tamanho: "
            f"{format_size(expected_size)}"
        )

        try:

            await message.download_media(
                file=str(
                    temp_file
                ),
                progress_callback=(
                    create_progress_callback(
                        safe_file_name
                    )
                ),
            )

            await remove_download_status(
                safe_file_name
            )

            if not file_is_complete(
                temp_file,
                expected_size,
            ):

                raise RuntimeError(
                    "Download terminou "
                    "com tamanho incorreto."
                )

            print(
                f"[DOWNLOAD OK] "
                f"{safe_file_name}"
            )

            await copy_queue.put(
                (
                    temp_file,
                    destination,
                    expected_size,
                )
            )

        except Exception as error:

            await remove_download_status(
                safe_file_name
            )

            print()
            print(
                f"[ERRO DOWNLOAD] "
                f"{safe_file_name}"
            )

            print(error)


# ============================================================
# MAIN
# ============================================================

async def main() -> None:

    check_drives()

    TEMP_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    DOWNLOAD_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print()
    print(
        "================================"
    )

    print(
        " TELEGRAM MANGA DOWNLOADER"
    )

    print(
        "================================"
    )

    print(
        f"Downloads simultâneos: "
        f"{MAX_DOWNLOADS}"
    )

    print(
        f"SSD: {TEMP_DIR}"
    )

    print(
        f"Cartão: {DOWNLOAD_DIR}"
    )

    print()

    semaphore = asyncio.Semaphore(
        MAX_DOWNLOADS
    )

    copy_queue = asyncio.Queue()

    copy_task = asyncio.create_task(
        copy_worker(
            copy_queue
        )
    )

    status_task = asyncio.create_task(
        status_worker()
    )

    tasks = []

    async for message in client.iter_messages(
        GROUP,
        reverse=True,
    ):

        if not message.file:
            continue

        if not message.file.name:
            continue

        extension = Path(
            message.file.name
        ).suffix.lower()

        if extension not in EXTENSIONS:
            continue

        task = asyncio.create_task(
            download_file(
                semaphore,
                message,
                copy_queue,
            )
        )

        tasks.append(
            task
        )

    print(
        f"{len(tasks)} arquivos "
        f"encontrados."
    )

    await asyncio.gather(
        *tasks
    )

    print()
    print(
        "Downloads finalizados."
    )

    print(
        "Aguardando cópias "
        "restantes..."
    )

    await copy_queue.join()

    await copy_queue.put(
        None
    )

    await copy_task

    status_task.cancel()

    try:
        await status_task
    except asyncio.CancelledError:
        pass

    print()
    print(
        "================================"
    )

    print(
        "FINALIZADO"
    )

    print(
        "================================"
    )

    print(
        f"SSD livre: "
        f"{format_size(get_free_space(TEMP_DIR))}"
    )

    print(
        f"Cartão livre: "
        f"{format_size(get_free_space(DOWNLOAD_DIR))}"
    )


# ============================================================
# TELEGRAM
# ============================================================

client = TelegramClient(
    "telegram_session",
    API_ID,
    API_HASH,
)


with client:

    client.loop.run_until_complete(
        main()
    )
