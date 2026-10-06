"""Create a small fictional text PDF without external dependencies."""
from pathlib import Path


def sample_pdf():
    lines = ["Fictional Candidate - demonstration only", "Skills", "Python, Django, PostgreSQL, Git",
             "Experience", "Backend Developer, Example Labs, 2023-2025",
             "Built Python Django REST APIs using PostgreSQL.", "Education",
             "BS Computer Science, Fictional University, 2023"]
    commands = ["BT /F1 12 Tf 50 780 Td"]
    for index, line in enumerate(lines):
        escaped = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        commands.append(("0 -24 Td " if index else "") + f"({escaped}) Tj")
    commands.append("ET")
    stream = "\n".join(commands).encode("ascii")
    objects = [b"<< /Type /Catalog /Pages 2 0 R >>",
               b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
               b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
               b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
               b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream"]
    content = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, 1):
        offsets.append(len(content))
        content.extend(f"{index} 0 obj\n".encode() + obj + b"\nendobj\n")
    xref = len(content)
    content.extend(f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]:
        content.extend(f"{offset:010d} 00000 n \n".encode())
    content.extend(f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    return bytes(content)


if __name__ == "__main__":
    target = Path(__file__).resolve().parent.parent / "data/sample_resume.pdf"
    target.write_bytes(sample_pdf())
    print(f"Created fictional sample: {target}")
