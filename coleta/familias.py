"""Famílias de procedimentos (códigos SIGTAP) acompanhadas no painel. Códigos conferidos no catálogo do InfoSaúde (Região Norte, 08/11/2026)."""
FAMILIAS = {
    "p_cito":     ("Coleta de citopatológico do colo do útero", ["0201020033", "0201020076", "0203010086"]),
    "p_diu":      ("Inserção de DIU", ["0301040141", "0301040028", "0301040222"]),
    "p_implante": ("Inserção de implante contraceptivo (etonogestrel)", ["0301040176"]),
    "p_ts_sif":   ("Teste rápido de sífilis", ["0214010082", "0214010074", "0214010252", "0214010260"]),
    "p_penic":    ("Penicilina para tratamento de sífilis", ["0301100241"]),
    "p_ts_hiv":   ("Teste rápido de HIV", ["0214010040", "0214010058", "0214010279", "0214010287"]),
    "p_ts_hep":   ("Teste rápido de hepatites B e C", ["0214010090", "0214010236", "0214010228", "0214010309", "0214010295", "0214010244", "0214010104", "0214010317"]),
    "p_pe":       ("Exame do pé diabético", ["0301040095"]),
    "p_prenatal": ("Consulta de pré-natal (procedimento)", ["0301010110"]),
    "p_puerp":    ("Consulta puerperal", ["0301010129"]),
    "p_puer":     ("Puericultura (crescimento e desenvolvimento)", ["0301010277", "0301010269", "0301010080"]),
    "p_domic":    ("Visita e consulta domiciliar (nível superior e médio)", ["0301050147", "0101030029", "0301010137", "0101030010"]),
    "p_busca":    ("Busca ativa", ["0301050139"]),
    "p_acolh":    ("Escuta inicial e acolhimento com classificação de risco", ["0301040079", "0301060118"]),
    "p_pa":       ("Aferição de pressão arterial", ["0301100039"]),
    "p_antropo":  ("Peso, altura e avaliação antropométrica", ["0101040024", "0101040083", "0101040075"]),
    "p_glic":     ("Glicemia capilar", ["0214010015"]),
    "p_idoso":    ("Avaliação multidimensional da pessoa idosa", ["0301090033"]),
    "p_curativo": ("Curativos", ["0301100276", "0401010015", "0301100284"]),
    "p_cirurg":   ("Pequenas cirurgias e retirada de pontos", ["0301100152", "0401010066", "0401010031", "0401020177", "0401010104", "0401010058"]),
    "p_med":      ("Administração de medicamentos", ["0301100209", "0301100195", "0301100217", "0301100225", "0301100101"]),
    "p_tabag":    ("Cessação do tabagismo", ["0301080011", "0301010099"]),
    "p_prep":     ("Profilaxia pré-exposição (PrEP)", ["0301010439", "0301010447"]),
    "p_pic":      ("Práticas integrativas (auriculoterapia, acupuntura, fitoterapia)", ["0309050049", "0309050022", "0309050014", "0309050030", "0309050200"]),
}
COD2FAM = {c: k for k, (_, cods) in FAMILIAS.items() for c in cods}
assert len(COD2FAM) == sum(len(c) for _, c in FAMILIAS.values()), "código repetido em duas famílias"
