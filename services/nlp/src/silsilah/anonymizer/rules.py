# Copyright (c) 2026 Vassel Goleyu. All rights reserved.
"""Daftar kata untuk membedakan nama orang dari lembaga, jabatan, dan kata umum. Semua huruf kecil."""

# Sapaan kekerabatan/sosial; setelah ini nama huruf kecil di chat ("pak joko") juga disamarkan.
KIN_HONORIFICS = frozenset("bapak bpk pak ibu bu kakak kak mas mbak mba abang bang adik adek dik dek".split())
# Sapaan lain dan gelar; nama sesudahnya harus berhuruf kapital.
OTHER_HONORIFICS = frozenset(
    """om tante teh aa akang kang cak ning uda uni bli mbok tuan nyonya ny nona sdr sdri saudara saudari
    eyang mbah kakek nenek opa oma bro sis hj haji hajah ustadz ustaz ustadzah ustazah kyai kiai gus romo
    pastor pendeta pdt syekh habib dr drg prof ir drs dra""".split()
)
# Penanda atribusi yang biasanya diikuti nama orang.
ATTRIBUTION = ("a.n", "a/n", "atas nama", "nama", "cp", "contact person", "pelapor", "penerima")
# Gelar yang boleh bertumpuk di depan nama ("Prof. Dr. Ir. Siti").
TITLES = frozenset("dr drg prof ir drs dra h hj haji ustadz ustaz kyai kiai".split())
# Penghubung di dalam nama ("Ahmad bin Abdullah").
NAME_CONNECTORS = frozenset("bin binti van der de al el".split())

# Kata lembaga: span yang mengandung salah satunya TIDAK disamarkan (lembaga adalah bagian mutasi).
INSTITUTION_WORDS = frozenset(
    """kementerian kemenkes kemendikbud kemensos kominfo komdigi dinas badan lembaga komisi dewan majelis
    rs rsud rsup rumah sakit puskesmas klinik universitas univ institut sekolah sd smp sma smk madrasah
    pesantren bank pt cv tbk yayasan koperasi perusahaan pemerintah pemkot pemkab pemprov pemda kabupaten
    provinsi kota desa kelurahan kecamatan polri polda polres polsek tni kodim koramil kodam kpu bawaslu
    bpjs pln pdam pertamina bpom who unicef unesco pbb asean mui nu muhammadiyah kpk ojk bi bmkg bnpb bpbd
    basarnas dpr dprd mpr ma mk kejaksaan pengadilan kepolisian satgas partai fakultas""".split()
)

# Jabatan dan peran: tetap terlihat, menghentikan penangkapan nama ("Pak Menteri", "Bu RT").
ROLE_WORDS = frozenset(
    """presiden wapres wakil menteri menkes gubernur bupati walikota wali camat lurah kades kadus kepala
    ketua sekretaris bendahara direktur dirut manajer manager admin pejabat petugas pegawai staf jubir
    kapolri kapolda kapolres kapolsek panglima jenderal kolonel komandan danramil babinsa bhabinkamtibmas
    dokter bidan perawat mantri guru dosen rektor dekan polisi tentara satpam sopir ojol kurir rt rw
    pendeta""".split()
)

# Kata umum yang sering muncul sesudah sapaan tetapi bukan nama.
COMMON_WORDS = frozenset(
    """ini itu tersebut yang dan atau serta juga tapi tetapi kalau kalo klo jika karena krn sudah udah sdh
    belum blm akan mau bisa harus tolong mohon minta sedang lagi masih baru tadi td besok kemarin nanti
    sekarang skrg hari minggu bulan tahun di ke dari dr untuk utk buat dengan dgn sama pada kepada oleh
    saya aku gue gw kamu anda dia beliau kami kita mereka semua sekalian sekalian2 bilang blg kata ngomong
    bicara datang pergi pulang kerja sakit hamil menyusui tua muda sehat kota rumah tangga kantor pasar
    kampung warga tidak tdk gak ga nggak enggak ya iya yah nih tuh deh dong sih kok aja saja pun lah
    tahu tau lihat liat cek info pesan kabar berita hati waspada""".split()
)

# Bidang jabatan ("Menteri Kesehatan"): bukan nama dan bukan lembaga, jadi nama sesudahnya tetap disamarkan.
PORTFOLIO_WORDS = frozenset(
    """kesehatan keuangan agama pendidikan sosial pertahanan keamanan luar dalam negeri perhubungan pertanian
    perdagangan perindustrian kelautan perikanan ketenagakerjaan komunikasi informatika digital hukum ham
    pariwisata koordinator bumn energi lingkungan kehutanan perumahan investasi""".split()
)
# Label dokumen yang sering ditandai NER sebagai nama ("NIK: [NIK]").
DOCUMENT_WORDS = frozenset(
    "nik ktp kk npwp sim paspor rek rekening norek no nomor telp tlp hp wa email alamat".split()
)

STOP_WORDS = (
    KIN_HONORIFICS
    | OTHER_HONORIFICS
    | INSTITUTION_WORDS
    | ROLE_WORDS
    | COMMON_WORDS
    | PORTFOLIO_WORDS
    | DOCUMENT_WORDS
)
