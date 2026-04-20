#!/usr/bin/env python3
"""Reescreve Subject de arquivos .patch trocando HU Azure por id GitLab.

Unifica o comportamento antes dividido entre:
- remap_patch_subjects.sh
- remap_patch_subjects.awk
"""

from __future__ import annotations

import argparse
import base64
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Dict


class AbortedExecution(Exception):
    """Sinaliza abort total solicitado pelo usuário."""


class RemapPatchSubjects:
    DEFAULT_ID_PATTERNS: list[str] = [
        r"[Hh][Uu][\s_\-#]*([0-9][0-9\s]{0,20})",
        r"(?:TASK|TASKS?)[\s_\-#]*([0-9][0-9\s]{0,20})",
        r"#[ \t]*([0-9][0-9 \t]{0,20})",
    ]
    ID_PATTERNS: list[str] = DEFAULT_ID_PATTERNS.copy()
    MIN_ID_DIGITS = 4
    _COMPILED_ID_PATTERNS: list[re.Pattern[str]] | None = None

    def __init__(self, mapfile: Path, patches_dir: Path, dryrun: bool) -> None:
        self.mapfile = mapfile
        self.patches_dir = patches_dir
        self.dryrun = dryrun
        self.mapping: Dict[str, str] = {}
        self.backed: Dict[str, bool] = {}
        self.aborted = False
        self.backup_root = Path(tempfile.mkdtemp(prefix="remap_patch_backup_")) if not dryrun else None

    @staticmethod
    def err(message: str) -> None:
        print(message, file=sys.stderr)

    @staticmethod
    def load_map(mapfile: Path) -> Dict[str, str]:
        data: Dict[str, str] = {}
        pattern = re.compile(r'"(\d+)"\s*:\s*"(\d+)"')
        with mapfile.open("r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                found = pattern.search(line)
                if found:
                    data[found.group(1)] = found.group(2)
        return data

    @staticmethod
    def decode_qp(payload: str) -> str:
        out: list[str] = []
        i = 0
        size = len(payload)
        while i < size:
            c = payload[i]
            if c == "_":
                out.append(" ")
                i += 1
                continue
            if c == "=" and i + 2 < size:
                h = payload[i + 1 : i + 3]
                if re.fullmatch(r"[0-9A-Fa-f]{2}", h):
                    out.append(chr(int(h, 16)))
                    i += 3
                    continue
            out.append(c)
            i += 1
        return "".join(out)

    @staticmethod
    def decode_b64(payload: str) -> str:
        try:
            return base64.b64decode(payload, validate=False).decode("latin-1", errors="ignore")
        except Exception:
            return ""

    @classmethod
    def decode_mime_header(cls, text: str) -> str:
        out = ""
        s = text
        while True:
            pos = s.find("=?")
            if pos < 0:
                break

            out += s[:pos]
            rest = s[pos + 2 :]

            i = rest.find("?")
            if i < 0:
                out += "=?" + rest
                return out
            charset = rest[:i]
            rest = rest[i + 1 :]

            i = rest.find("?")
            if i < 0:
                out += f"=?{charset}?" + rest
                return out
            encoding = rest[:i]
            rest = rest[i + 1 :]

            endp = rest.find("?=")
            if endp < 0:
                out += f"=?{charset}?{encoding}?" + rest
                return out

            body = rest[:endp]
            s = rest[endp + 2 :]

            if re.fullmatch(r"[qQ]", encoding):
                out += cls.decode_qp(body)
            elif re.fullmatch(r"[bB]", encoding):
                out += cls.decode_b64(body)
            else:
                out += f"=?{charset}?{encoding}?{body}?="

        return out + s

    @staticmethod
    def _append_unique(target: list[str], values: list[str]) -> None:
        for value in values:
            if value not in target:
                target.append(value)

    @staticmethod
    def _normalize_id(raw: str) -> str:
        return re.sub(r"\D", "", raw)

    @classmethod
    def configure_id_patterns(cls, patterns: list[str], min_digits: int) -> None:
        valid = [item.strip() for item in patterns if item and item.strip()]
        cls.ID_PATTERNS = valid if valid else cls.DEFAULT_ID_PATTERNS.copy()
        cls.MIN_ID_DIGITS = max(1, int(min_digits))
        cls._COMPILED_ID_PATTERNS = None

    @classmethod
    def compiled_id_patterns(cls) -> list[re.Pattern[str]]:
        if cls._COMPILED_ID_PATTERNS is not None:
            return cls._COMPILED_ID_PATTERNS

        compiled: list[re.Pattern[str]] = []
        for pattern in cls.ID_PATTERNS:
            try:
                compiled.append(re.compile(pattern, re.IGNORECASE))
            except re.error:
                cls.err(f"[aviso] padrao regex invalido ignorado: {pattern}")

        if not compiled:
            compiled = [re.compile(item, re.IGNORECASE) for item in cls.DEFAULT_ID_PATTERNS]

        cls._COMPILED_ID_PATTERNS = compiled
        return compiled

    @classmethod
    def load_patterns_map(cls, patterns_file: Path) -> tuple[list[str], int]:
        patterns: list[str] = []
        min_digits = cls.MIN_ID_DIGITS
        in_patterns_block = False

        with patterns_file.open("r", encoding="utf-8", errors="replace") as fh:
            for raw in fh:
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue

                if ":" in line and not line.startswith("-"):
                    key, _, value = line.partition(":")
                    key = key.strip().lower()
                    value = value.strip()

                    if key in {"id_patterns", "patterns", "hu_patterns"}:
                        in_patterns_block = True
                        # suporta lista inline: id_patterns: ["...", "..."]
                        if value.startswith("[") and value.endswith("]"):
                            content = value[1:-1]
                            for part in content.split(","):
                                item = part.strip().strip("'\"")
                                if item:
                                    patterns.append(item)
                        continue

                    in_patterns_block = False
                    if key == "min_id_digits":
                        try:
                            min_digits = int(value)
                        except ValueError:
                            cls.err(f"[aviso] min_id_digits invalido no arquivo de padroes: {value}")
                    continue

                if in_patterns_block and line.startswith("-"):
                    item = line[1:].strip().strip("'\"")
                    if item:
                        patterns.append(item)

        return patterns, min_digits

    @classmethod
    def extract_hu_ids(cls, text: str) -> list[str]:
        ids: list[str] = []
        for pattern in cls.compiled_id_patterns():
            if pattern.groups < 1:
                cls.err(f"[aviso] padrao sem grupo de captura ignorado: {pattern.pattern}")
                continue
            values_raw = [match.group(1) for match in pattern.finditer(text)]
            values = [cls._normalize_id(value) for value in values_raw]
            cls._append_unique(ids, [value for value in values if len(value) >= cls.MIN_ID_DIGITS])

        return ids

    @classmethod
    def extract_hu_id(cls, subject: str) -> str:
        ids = cls.extract_hu_ids(subject)
        return ids[0] if ids else ""

    @classmethod
    def extract_hu_from_body(cls, content: str) -> str:
        ids = cls.extract_hu_ids_from_body(content)
        return ids[0] if ids else ""

    @classmethod
    def extract_hu_ids_from_body(cls, content: str) -> list[str]:
        """Extrai todos os IDs candidatos do corpo completo do patch (commit message)."""
        lines = content.split("\n")
        message_lines = []
        for line in lines:
            if line.startswith("diff --git"):
                break
            message_lines.append(line)

        body = " ".join(message_lines)
        return cls.extract_hu_ids(body)

    @classmethod
    def extract_hu_ids_from_filename(cls, filename: str) -> list[str]:
        ids = cls.extract_hu_ids(filename)

        # Procura números de 4-6 dígitos que NÃO estão no início do nome
        # (evita capturar o número sequencial do patch)
        base = os.path.basename(filename)
        base_without_prefix = re.sub(r"^\d+-", "", base)
        fallback_values = re.findall(
            rf"(?<![0-9])(\d{{{cls.MIN_ID_DIGITS},6}})(?![0-9])",
            base_without_prefix,
        )
        cls._append_unique(ids, fallback_values)
        return ids

    @classmethod
    def extract_hu_from_filename(cls, filename: str) -> str:
        ids = cls.extract_hu_ids_from_filename(filename)
        return ids[0] if ids else ""

    @staticmethod
    def _find_hash_id_span(subject: str) -> tuple[int, int] | None:
        for match in re.finditer(r"#[ \t]*([0-9][0-9 \t]{0,20})", subject):
            candidate = RemapPatchSubjects._normalize_id(match.group(1))
            if len(candidate) >= 4:
                return match.start(), match.end()
        return None

    @classmethod
    def strip_hu_suffix(cls, subject: str, gid: str, azure: str = "") -> str:
        match = re.search(r"[ \t]+[Hh][Uu][ \t]*#[ \t]*[0-9]+", subject)
        if match:
            return subject[: match.start()] + f" #{gid}"

        match = re.match(r"[Hh][Uu][ \t]*#[ \t]*[0-9]+", subject)
        if match:
            return f" #{gid}"

        span = cls._find_hash_id_span(subject)
        if span is not None:
            start, end = span
            return subject[:start] + f"#{gid}" + subject[end:]

        # Fallback: substitui o ID Azure quando estiver como número isolado
        # (ex.: feature/33120 -> feature/33099).
        if azure and re.fullmatch(r"\d+", azure):
            pattern = rf"(?<!\d){re.escape(azure)}(?!\d)"
            if re.search(pattern, subject):
                return re.sub(pattern, gid, subject, count=1)

        return subject

    @staticmethod
    def read_tty_line() -> str:
        try:
            with open("/dev/tty", "r", encoding="utf-8", errors="replace") as tty:
                line = tty.readline()
        except OSError:
            line = sys.stdin.readline()

        return line.strip(" \t\r\n")

    @staticmethod
    def backup_key(filename: str) -> str:
        return filename.replace("\\", "_").replace("/", "_").replace(":", "_")

    def ensure_backup(self, filename: str) -> None:
        if self.dryrun or self.backup_root is None or filename in self.backed:
            return

        src = Path(filename)
        dst = self.backup_root / self.backup_key(filename)
        try:
            shutil.copy2(src, dst)
        except OSError:
            self.err(f"[erro] não foi possível fazer backup de: {filename}")
            raise SystemExit(1)
        self.backed[filename] = True

    def restore_all_from_backup(self) -> bool:
        if self.backup_root is None:
            return True

        ok = True
        for filename in self.backed:
            backup_file = self.backup_root / self.backup_key(filename)
            try:
                shutil.copy2(backup_file, filename)
            except OSError:
                self.err(f"[erro] falha ao restaurar: {filename}")
                ok = False

        if ok:
            shutil.rmtree(self.backup_root, ignore_errors=True)
        else:
            self.err(f"[aviso] Backups não apagados; pasta: {self.backup_root}")

        return ok

    def banner_skip_big(self, filename: str) -> None:
        self.err("")
        self.err("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        self.err("!!                                                          !!")
        self.err("!!   S K I P   -  este .patch NAO sera alterado agora      !!")
        self.err("!!                                                          !!")
        self.err("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        self.err(f"Arquivo: {filename}")
        self.err("Nada foi gravado neste patch. Os demais seguem em seguida.")
        self.err("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        self.err("")

    def banner_abort_big(self) -> None:
        total = len(self.backed)
        self.err("")
        self.err("##############################################################")
        self.err("##                                                          ##")
        self.err("##   A B O R T A R   T U D O                                ##")
        self.err("##   Restaurando o estado anterior a este comando          ##")
        self.err("##                                                          ##")
        self.err("##############################################################")
        self.err(f"Backups a restaurar: {total}")
        self.err("##############################################################")
        self.err("")

    def prompt_de_para(self, azure_detected: str, filename: str) -> str:
        self.err("")
        self.err("------------------------------------------------------------")
        self.err("Nao ha DE->PARA no arquivo de mapa para este commit.")
        self.err(f"Patch: {filename}")
        self.err(f"(Detectada HU/TASK Azure #{azure_detected} para este patch)")
        self.err("")
        self.err("Informe o mapeamento para continuar (Enter no DE = usar a HU detectada acima).")
        self.err("")

        print("HU Azure (DE): ", end="", file=sys.stderr, flush=True)
        azure_in = self.read_tty_line()

        if azure_in == "":
            azure_in = azure_detected
        elif not re.fullmatch(r"\d+", azure_in):
            self.err(f"[aviso] id invalido; usando a HU detectada no assunto: {azure_detected}")
            azure_in = azure_detected
        elif azure_in != azure_detected:
            self.err(
                f"[aviso] o assunto do patch continua com HU #{azure_detected}; "
                "o mapa gravado sera Azure "
                f"{azure_detected} -> GitLab (abaixo)."
            )

        self.err("")
        self.err("PARA (GitLab), escolha:")
        self.err("  * so digitos  = id no GitLab")
        self.err("  * s, skip ou Enter vazio = pular so este patch (SKIP - alerta grande no terminal)")
        self.err("  * a ou abort  = desfazer TUDO: voltar todos os .patch ja alterados nesta execucao")
        self.err("")
        print("HU GitLab (PARA): ", end="", file=sys.stderr, flush=True)

        para_in = self.read_tty_line()
        lower = para_in.lower()

        if lower in {"a", "abort"}:
            self.banner_abort_big()
            if self.restore_all_from_backup():
                self.err("[ok] Estado dos .patch restaurado (como antes de rodar o comando).")
            else:
                self.err("[aviso] Alguns arquivos podem nao ter sido restaurados; verifique manualmente.")
            self.aborted = True
            self.err("------------------------------------------------------------")
            raise AbortedExecution

        if lower in {"s", "skip"} or para_in == "":
            self.banner_skip_big(filename)
            self.err("------------------------------------------------------------")
            return ""

        if not re.fullmatch(r"\d+", para_in):
            self.err("[erro] HU GitLab (PARA): use so digitos, ou s / a (ver legenda acima).")
            self.err("------------------------------------------------------------")
            return ""

        self.mapping[azure_detected] = para_in
        self.err(f"[ok] Sessao: Azure {azure_detected} (DE) -> GitLab {para_in} (PARA)")
        self.err("------------------------------------------------------------")
        return para_in

    def process_content(self, content: str, filename: str) -> bool:
        pos = content.find("\n---\n")
        if pos < 0:
            self.err(f"[ignorar] {filename}: sem bloco ---")
            return False

        head = content[: pos + 1]
        tail = content[pos:]
        lines = head.split("\n")

        lo = None
        hi = None
        for idx, line in enumerate(lines):
            if line.startswith("Subject:"):
                lo = idx
                hi = idx
                while hi + 1 < len(lines) and re.match(r"^[ \t]", lines[hi + 1]):
                    hi += 1
                break

        if lo is None or hi is None:
            self.err(f"[ignorar] {filename}: sem Subject")
            return False

        raw = re.sub(r"^Subject:[ \t]*", "", lines[lo])
        for idx in range(lo + 1, hi + 1):
            tmp = re.sub(r"^[ \t]+", "", lines[idx])
            raw += " " + tmp

        decoded = self.decode_mime_header(raw)
        subject_ids = self.extract_hu_ids(decoded)
        filename_ids = self.extract_hu_ids_from_filename(filename)
        body_ids = self.extract_hu_ids_from_body(content)

        azure_candidates: list[str] = []
        self._append_unique(azure_candidates, subject_ids)
        self._append_unique(azure_candidates, filename_ids)
        self._append_unique(azure_candidates, body_ids)

        if not azure_candidates:
            self.err(f"[aviso] {filename}: nenhum HU/TASK no Subject, nome do arquivo ou corpo")
            return False

        if subject_ids:
            self.err(f"[info] {filename}: IDs no Subject: {', '.join(subject_ids)}")
        if filename_ids:
            self.err(f"[info] {filename}: IDs no nome: {', '.join(filename_ids)}")
        if body_ids:
            self.err(f"[info] {filename}: IDs no corpo: {', '.join(body_ids)}")

        azure = next((item for item in azure_candidates if item in self.mapping), azure_candidates[0])

        if azure not in self.mapping:
            if self.dryrun:
                self.err(
                    f"[erro] {filename}: HU/TASK Azure '{azure}' sem entrada no mapa "
                    "(dry-run: sem prompt)"
                )
                return False
            gid = self.prompt_de_para(azure, filename)
            if gid == "":
                return False
        else:
            gid = self.mapping[azure]

        new_subject = self.strip_hu_suffix(decoded, gid, azure=azure)
        if new_subject == decoded:
            self.err(f"[aviso] {filename}: assunto inalterado")
            return False

        out_lines = lines[:lo] + [f"Subject: {new_subject}"] + lines[hi + 1 :]
        out = "\n".join(out_lines)

        if self.dryrun:
            print(filename)
            return True

        self.ensure_backup(filename)
        tmp_name = f"{filename}.tmp"
        try:
            with open(tmp_name, "wb") as fh:
                fh.write((out + tail).encode("latin-1", errors="replace"))
            os.replace(tmp_name, filename)
        except OSError:
            self.err(f"[erro] {filename}: falha ao gravar")
            try:
                os.remove(tmp_name)
            except OSError:
                pass
            return False

        print(filename)
        return True

    def cleanup(self) -> None:
        if self.backup_root is not None:
            shutil.rmtree(self.backup_root, ignore_errors=True)


def usage(prog: str) -> None:
    print(
        f"Uso: {prog} [--dry-run] [--map <arquivo.yml>] [--patches-dir <pasta>] "
        "[--patterns-map <arquivo.yml>]"
    )
    print("Fallbacks por ambiente: MAP, PATCHES_DIR e PATTERNS_MAP")
    print("No prompt PARA: s, skip ou Enter = pular (alerta grande); a = abortar e restaurar tudo.")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Reescreve Subject de arquivos .patch usando mapa Azure->GitLab."
    )
    parser.add_argument("--dry-run", action="store_true", help="Simula sem alterar arquivos.")
    parser.add_argument(
        "--map",
        dest="mapfile",
        default=None,
        help="Arquivo YAML de mapeamento (fallback: env MAP).",
    )
    parser.add_argument(
        "--patches-dir",
        default=None,
        help="Pasta com .patch (fallback: env PATCHES_DIR).",
    )
    parser.add_argument(
        "--patterns-map",
        default=None,
        help="Arquivo YAML com regex de identificacao (fallback: env PATTERNS_MAP).",
    )
    return parser.parse_args(argv)


def main() -> int:
    args = parse_args(sys.argv[1:])

    map_raw = (args.mapfile or "").strip() or (os.environ.get("MAP") or "").strip()
    patches_raw = (args.patches_dir or "").strip() or (os.environ.get("PATCHES_DIR") or "").strip()
    patterns_raw = (args.patterns_map or "").strip() or (os.environ.get("PATTERNS_MAP") or "").strip()

    if not map_raw:
        print("[erro] informe --map ou defina MAP.", file=sys.stderr)
        return 1
    if not patches_raw:
        print("[erro] informe --patches-dir ou defina PATCHES_DIR.", file=sys.stderr)
        return 1

    mapfile = Path(map_raw).expanduser().resolve()
    patches_dir = Path(patches_raw).expanduser().resolve()
    default_patterns_map = Path(__file__).resolve().parent.parent / "map" / "hu-patterns.yml"
    patterns_file = Path(patterns_raw).expanduser().resolve() if patterns_raw else default_patterns_map

    if not mapfile.is_file():
        print(f"Arquivo de mapa nao encontrado: {mapfile}", file=sys.stderr)
        return 1

    if not patches_dir.is_dir():
        print(f"Pasta nao encontrada: {patches_dir}", file=sys.stderr)
        return 1

    if patterns_file.is_file():
        patterns, min_digits = RemapPatchSubjects.load_patterns_map(patterns_file)
        RemapPatchSubjects.configure_id_patterns(patterns, min_digits)
        print(
            f"[info] padroes de identificacao carregados: {patterns_file} "
            f"({len(RemapPatchSubjects.ID_PATTERNS)} regex, min_id_digits={RemapPatchSubjects.MIN_ID_DIGITS})",
            file=sys.stderr,
        )
    elif patterns_raw:
        print(f"[erro] arquivo de padroes nao encontrado: {patterns_file}", file=sys.stderr)
        return 1
    else:
        RemapPatchSubjects.configure_id_patterns(RemapPatchSubjects.DEFAULT_ID_PATTERNS, 4)
        print("[info] usando padroes internos padrao de identificacao HU/TASK.", file=sys.stderr)

    patch_files = sorted(str(path) for path in patches_dir.glob("*.patch"))
    if not patch_files:
        print(f"Nenhum .patch em {patches_dir}", file=sys.stderr)
        return 1

    runner = RemapPatchSubjects(mapfile=mapfile, patches_dir=patches_dir, dryrun=args.dry_run)
    runner.mapping = runner.load_map(mapfile)

    if not runner.mapping:
        runner.err(
            f"Aviso: mapa vazio em {mapfile} - os pares DE->PARA serao pedidos no terminal quando faltar entrada."
        )

    updated = 0
    total = 0

    try:
        for patch in patch_files:
            total += 1
            with open(patch, "rb") as fh:
                content = fh.read().decode("latin-1", errors="replace")
            if runner.process_content(content, patch):
                updated += 1
    except AbortedExecution:
        runner.err("")
        runner.err("Execucao interrompida (abort). Codigo de saida 2.")
        return 2
    finally:
        runner.cleanup()

    print(f"Concluido: {updated}/{total} patch(es) com Subject atualizado.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
