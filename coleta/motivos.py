"""Linhas de cuidado por CID-10 (motivos de consulta). Primeira regra que casar vale; sem CID = m_sem.
Um atendimento pode ter mais de um CID: as contagens são de CID registrados, não de atendimentos distintos."""
MOTIVOS = [  # id, nome, prefixos
    ("m_rx", "Prescrição de repetição (Z76.0)", ("Z760",)),
    ("m_crianca", "Saúde da criança (puericultura)", ("Z001", "Z762")),
    ("m_admin", "Demandas administrativas e exame geral (atestado, exames)", ("Z00", "Z02", "Z76", "Z10")),
    ("m_gravidez", "Gravidez, pré-natal e puerpério", ("O", "Z32", "Z33", "Z34", "Z35", "Z36", "Z39")),
    ("m_contracep", "Planejamento familiar e contracepção", ("Z30",)),
    ("m_rastreio", "Rastreamento (câncer e outros)", ("Z11", "Z12", "Z13")),
    ("m_has", "Hipertensão", ("I10", "I11", "I12", "I13", "I15")),
    ("m_dm", "Diabetes", ("E10", "E11", "E12", "E13", "E14")),
    ("m_obesi", "Obesidade, desnutrição e dislipidemia", ("E65", "E66", "E67", "E68", "E40", "E41", "E42", "E43", "E44", "E45", "E46", "E78")),
    ("m_card", "Outras doenças do aparelho circulatório", ("I",)),
    ("m_mental", "Saúde mental", ("F", "R45")),
    ("m_resp_ag", "Infecções respiratórias agudas e COVID", ("J0", "J1", "J20", "J21", "J22", "U07", "B34")),
    ("m_asma", "Asma, DPOC e rinite", ("J3", "J4")),
    ("m_arbo", "Dengue, arboviroses e febre", ("A90", "A91", "A92", "A97", "R50")),
    ("m_ist", "IST, HIV e sífilis", ("A5", "A6", "B20", "B21", "B22", "B23", "B24", "Z20", "Z21")),
    ("m_tbhan", "Tuberculose e hanseníase", ("A15", "A16", "A17", "A18", "A19", "A30")),
    ("m_urogin", "Urinário e ginecológico", ("N",)),
    ("m_osteo", "Dor e osteomuscular", ("M", "R52")),
    ("m_pele", "Pele", ("L",)),
    ("m_trauma", "Lesões e traumas", ("S", "T")),
    ("m_dig", "Digestivo", ("K", "A09")),
    ("m_sint", "Outros sintomas e sinais", ("R",)),
    ("m_endo", "Endócrino e metabólico (tireoide e outros)", ("E",)),
    ("m_neuro", "Neurológico (cefaleia, epilepsia, sono)", ("G",)),
    ("m_olho", "Olhos e ouvidos", ("H",)),
    ("m_infec", "Outras infecções e parasitoses", ("A", "B")),
    ("m_sangue", "Anemia, sangue e tumores", ("C", "D")),
    ("m_zoutros", "Aconselhamento, hábitos de vida e outros fatores (Z)", ("Z",)),
    ("m_outros", "Outros diagnósticos", ("",)),
]
SEM_CID = ("m_sem", "Sem CID registrado")
NOMES = {k: n for k, n, _ in MOTIVOS}; NOMES[SEM_CID[0]] = SEM_CID[1]
def fam_cid(cid):
    c = str(cid or "").strip().upper().replace(".", "")
    if not c or c in ("-", "NONE", "NULL", "(EM BRANCO)"): return SEM_CID[0]
    for k, _, pref in MOTIVOS:
        if any(c.startswith(p) for p in pref): return k
    return "m_outros"
