"""Linhas de cuidado dos motivos de consulta. O CID-10 vale primeiro (primeira regra que casar); quando o registro
não tem CID, entra o CIAP-2 (fam_ciap); sem nenhum dos dois = m_sem.
Um atendimento pode ter mais de um código: as contagens são de códigos registrados, não de atendimentos distintos."""
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
SEM_CID = ("m_sem", "Sem CID nem CIAP registrado")
NOMES = {k: n for k, n, _ in MOTIVOS}; NOMES[SEM_CID[0]] = SEM_CID[1]
def fam_cid(cid):
    c = str(cid or "").strip().upper().replace(".", "")
    if not c or c in ("-", "NONE", "NULL", "(EM BRANCO)"): return SEM_CID[0]
    for k, _, pref in MOTIVOS:
        if any(c.startswith(p) for p in pref): return k
    return "m_outros"

# ---- CIAP-2 (só para registros sem CID). Tabela de 16/11/2026, feita sobre os 709 códigos da dCiap do InfoSaúde; validação clínica da Rebeca pendente.
# Regra: código específico (CIAP_COD) > capítulo (CIAP_CAP). Sintomas ficam na linha do aparelho; neoplasias vão com "sangue e tumores", como no CID.
def _c(letra, *nums): return [f"{letra}{n:02d}" for n in nums]
def _f(letra, a, b): return [f"{letra}{n:02d}" for n in range(a, b + 1)]
CIAP_COD = {}
for _k, _l in (
    ("m_admin", _c("A", 97, 98)),                                            # sem doença; medicina preventiva/manutenção da saúde (equivale ao exame geral Z00)
    ("m_crianca", ["ABP004"] + _c("T", 4) + _c("A", 16)),
    ("m_gravidez", ["ABP001", "ABP002"]),
    ("m_contracep", ["ABP003"] + _f("W", 10, 15) + _c("Y", 13, 14)),
    ("m_rastreio", ["ABP022", "ABP023", "ABP024"] + _c("X", 86)),            # X86 = esfregaço de Papanicolau
    ("m_has", ["ABP005"] + _c("K", 25, 85, 86, 87)),
    ("m_dm", ["ABP006"] + _c("T", 89, 90)),
    ("m_obesi", ["ABP007", "ABP008"] + _c("T", 7, 8, 82, 83, 91, 93)),
    ("m_mental", ["ABP011", "ABP012", "ABP013", "ABP014"]),
    ("m_asma", ["ABP009", "ABP010"] + _c("R", 79, 95, 96, 97)),
    ("m_arbo", ["ABP019"] + _c("A", 3, 77)),                                 # febre; dengue e outras doenças virais
    ("m_ist", ["ABP020"] + _c("B", 25, 90) + _c("X", 23, 70, 71, 73, 90, 91, 92) + _c("Y", 25, 70, 71, 72, 76)),
    ("m_tbhan", ["ABP017", "ABP018"] + _c("A", 70, 78)),                     # A78 = hanseníase e outras doenças infecciosas NE
    ("m_osteo", _c("A", 1)),                                                 # dor generalizada/múltipla
    ("m_trauma", _c("A", 80, 81, 82, 84, 86, 88) + _c("B", 76, 77) + _c("D", 79, 80) + _c("F", 75, 76, 79) + _f("H", 76, 79) + _f("L", 72, 81) + _c("L", 96)
                 + _f("N", 79, 81) + _c("R", 87, 88) + _f("S", 12, 19) + _c("U", 80) + _c("W", 75) + _c("X", 82) + _c("Y", 80)),
    ("m_infec", _f("A", 71, 76) + _c("D", 71, 72, 96) + _f("N", 70, 73)),   # exantemas, caxumba, hepatite viral, parasitoses, infecções neurológicas
    ("m_sangue", _c("A", 79) + _f("D", 74, 78) + _c("F", 74) + _c("H", 75) + _c("K", 72) + _c("L", 71, 97) + _f("N", 74, 76) + _c("R", 84, 85, 86, 92)
                 + _f("S", 77, 79) + _f("T", 71, 73) + _f("U", 75, 79) + _c("W", 72, 73) + _f("X", 75, 81) + _f("Y", 77, 79)),
    ("m_outros", _c("A", 85, 87, 89, 90, 92, 93, 94, 95, 96, 99)),           # efeitos adversos, malformação, alergia NE, perinatal, outras doenças gerais
    ("m_zoutros", ["ABP015"]),
):
    for _x in _l:
        assert _x not in CIAP_COD, _x
        CIAP_COD[_x] = _k
CIAP_CAP = {"A": "m_sint", "B": "m_sangue", "D": "m_dig", "F": "m_olho", "H": "m_olho", "K": "m_card", "L": "m_osteo", "N": "m_neuro", "P": "m_mental",
            "R": "m_resp_ag", "S": "m_pele", "T": "m_endo", "U": "m_urogin", "W": "m_gravidez", "X": "m_urogin", "Y": "m_urogin", "Z": "m_zoutros"}
def fam_ciap(ciap):
    c = str(ciap or "").strip().upper()
    if not c or c in ("-", "NONE", "NULL", "(EM BRANCO)"): return SEM_CID[0]
    return CIAP_COD.get(c) or CIAP_CAP.get(c[0], "m_outros")
