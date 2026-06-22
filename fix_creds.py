from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.user import User
from app.models.credential import Credential
from app.core.security import encrypt_aes

db_url = 'postgresql://postgres.ondyyjkceprlfkorlvnp:xsgnAjSyekoUiA5v@aws-1-us-east-1.pooler.supabase.com:5432/postgres?sslmode=require'
engine = create_engine(db_url)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

# Delete the bad credentials (only those we just added with short titles)
bad_creds = db.query(Credential).filter(Credential.title.in_(["Correo", "CRM", "PC", "Vocalcom"])).all()
for c in bad_creds:
    db.delete(c)
db.commit()
print("Bad credentials deleted.")

# List of credentials to process
# Format: (owner_email, full_name, (sysLabel, category, username, password, url))
users_data = [
    ("cgaetet@geoinfobusiness.cl", "CATHERINE ELENA GAETE TAGLE", [
        ("Correo", "Correo Corporativo", "cgaetet@geoinfobusiness.cl", "Cgaete.2026", None),
        ("CRM", "CRM", "cgaetet@geoinfobusiness.cl", "Cgaete.2026", None),
        ("PC", "Sistemas", "Catherine.gaete", "Geimser.2026", None),
        ("Vocalcom", "Telefonía", "C.gaete", "Cg.2026", "2000")
    ]),
    ("izamoranoc@geoinfobusiness.cl", "ISABEL ANDREA ZAMORANO CAMPOS", [
        ("Correo", "Correo Corporativo", "izamoranoc@geoinfobusiness.cl", "Izamorano.2026", None),
        ("CRM", "CRM", "izamoranoc@geoinfobusiness.cl", "Izamorano.2026", None),
        ("PC", "Sistemas", "Isabel.Zamorano", "Geimser.2026", None),
        ("Vocalcom", "Telefonía", "I.zamorano", "Iz.2026", "2001")
    ]),
    ("eduranb@geoinfobusiness.cl", "ELIZABETH CAROLINA DURAN BRAVO", [
        ("Correo", "Correo Corporativo", "eduranb@geoinfobusiness.cl", "Eduran.2026", None),
        ("Vocalcom", "Telefonía", "E.duran", "Ed.2026", "2002")
    ]),
    ("amoralesc@geoinfobusiness.cl", "ANA KARINA MORALES CARMONA", [
        ("Correo", "Correo Corporativo", "amoralesc@geoinfobusiness.cl", "Amorales.2026", None),
        ("CRM", "CRM", "amoralesc@geoinfobusiness.cl", "Amorales.2026", None),
        ("PC", "Sistemas", "ana.morales", "Geimser.2026", None),
        ("Vocalcom", "Telefonía", "A.morales", "Am.2026", "2004")
    ]),
    ("kordonezc@geoinfobusiness.cl", "KAREN ALEJANDRA ORDOÑEZ CONTRERAS", [
        ("Correo", "Correo Corporativo", "kordonezc@geoinfobusiness.cl", "Kordonez.2026", None),
        ("CRM", "CRM", "kordonezc@geoinfobusiness.cl", "Ko.2026", None),
        ("PC", "Sistemas", "Karen.ordoñez", "Geimser.2026", None),
        ("Vocalcom", "Telefonía", "K.ordonez", "Ko.2026", "2005")
    ]),
    ("xcofres@geoinfobusiness.cl", "XIMENA NAYADE COFRE SILVA", [
        ("Correo", "Correo Corporativo", "xcofres@geoinfobusiness.cl", "Xcofre.2026", None),
        ("CRM", "CRM", "xcofres@geoinfobusiness.cl", "Xc.2026", None),
        ("PC", "Sistemas", "Ximena.cofre", "Geimser.2026", None),
        ("Vocalcom", "Telefonía", "X.cofre", "Xc.2026", "2006")
    ]),
    ("azunigab@geoinfobusiness.cl", "ANDREA SOLEDAD ZUÑIGA BUSTOS", [
        ("Correo", "Correo Corporativo", "azunigab@geoinfobusiness.cl", "Azuñiga.2026", None),
        ("CRM", "CRM", "azunigab@geoinfobusiness.cl", "Az.2026", None),
        ("PC", "Sistemas", "Andrea.zuñiga", "Geimser.2026", None),
        ("Vocalcom", "Telefonía", "A.zuniga", "Az.2026", "2008")
    ]),
    ("avildosolac@geoinfobusiness.cl", "ANDRES RODRIGO VILDOSOLA CASTILLO", [
        ("Correo", "Correo Corporativo", "avildosolac@geoinfobusiness.cl", "Avildosola.2026", None),
        ("CRM", "CRM", "avildosolac@geoinfobusiness.cl", "Avildosola.2026", None),
        ("PC", "Sistemas", "andres.vildosola", "Geimser.2026", None),
        ("Vocalcom", "Telefonía", "A.vildosola", "Av.2026", "2009")
    ]),
    ("maranedab@geoinfobusiness.cl", "MARCELO ENRIQUE ARANEDA BRAVO", [
        ("Correo", "Correo Corporativo", "maranedab@geoinfobusiness.cl", "Maraneda.2026", None),
        ("CRM", "CRM", "maranedab@geoinfobusiness.cl", "Maraneda.2026", None),
        ("PC", "Sistemas", "marcelo.araneda", "Geimser.2026", None),
        ("Vocalcom", "Telefonía", "M.araneda", "Ma.2026", "2010")
    ]),
    ("rfigueroaa@geoinfobusiness.cl", "RODRIGO EDUARDO FIGUEROA ARANCIBIA", [
        ("Correo", "Correo Corporativo", "rfigueroaa@geoinfobusiness.cl", "Rfigueroa.2026", None),
        ("CRM", "CRM", "rfigueroaa@geoinfobusiness.cl", "Rfigueroa.2026", None),
        ("PC", "Sistemas", "Rodrigo.figueroa", "Geimser.2026", None),
        ("Vocalcom", "Telefonía", "R.figueroa", "Rf.2026", "2011")
    ]),
    ("jpozoc@geoinfobusiness.cl", "JENNY DEL CARMEN POZO CORREA", [
        ("Correo", "Correo Corporativo", "jpozoc@geoinfobusiness.cl", "Jpozo.2026", None),
        ("PC", "Sistemas", "Jenny.pozo", "Geimser.2026", None),
        ("Vocalcom", "Telefonía", "J.pozo", "Jp.2026", "2013")
    ]),
    ("jsanhuezav@geoinfobusiness.cl", "JOSE MIGUEL SANHUEZA VILLEGAS", [
        ("Correo", "Correo Corporativo", "jsanhuezav@geoinfobusiness.cl", "Jsanhueza.2026", None),
        ("CRM", "CRM", "jsanhuezav@geoinfobusiness.cl", "Jsanhueza.2026", None),
        ("PC", "Sistemas", "jose.sanhueza", "Geimser.2026", None),
        ("Vocalcom", "Telefonía", "J.sanhueza", "Js.2026", "2014")
    ]),
    ("mmoram@geoinfobusiness.cl", "MARCELA LILIANA MORA MORALES", [
        ("Correo", "Correo Corporativo", "mmoram@geoinfobusiness.cl", "Mmora.2026", None),
        ("CRM", "CRM", "mmoram@geoinfobusiness.cl", "Mmora.2026", None),
        ("PC", "Sistemas", "marcela.mora", "Geimser.2026", None),
        ("Vocalcom", "Telefonía", "M.mora", "Mm.2026", "2015")
    ]),
    ("cpenag@geoinfobusiness.cl", "CLAUDIA ESTER PEÑA GARCES", [
        ("Correo", "Correo Corporativo", "cpenag@geoinfobusiness.cl", "Cpena.2026", None),
        ("CRM", "CRM", "cpenag@geoinfobusiness.cl", "Cpena.2026", None),
        ("PC", "Sistemas", "claudia.pena", "Geimser.2026", None),
        ("Vocalcom", "Telefonía", "C.pena", "Cp.2026", "2016")
    ]),
    ("vbritol@geoinfobusiness.cl", "VICENTE JOSE BRITO LEON", [
        ("Correo", "Correo Corporativo", "vbritol@geoinfobusiness.cl", "Vbrito.2026", None),
        ("CRM", "CRM", "vbritol@geoinfobusiness.cl", "Vbrito.2026", None),
        ("PC", "Sistemas", "vicente.brito", "Geimser.2026", None),
        ("Vocalcom", "Telefonía", "V.brito", "Vb.2026", "2017")
    ]),
    ("eperezm@geoinfobusiness.cl", "EDUARDO RODRIGO PEREZ MOYA", [
        ("Correo", "Correo Corporativo", "eperezm@geoinfobusiness.cl", "Eperez.2026", None),
        ("CRM", "CRM", "eperezm@geoinfobusiness.cl", "Eperez.2026", None),
        ("PC", "Sistemas", "Eduardo.perez", "Geimser.2026", None),
        ("Vocalcom", "Telefonía", "E.perez", "Ep.2026", "2007")
    ]),
    ("khalabyd@geoinfobusiness.cl", "KARINA HALABY DONOSO", [
        ("Correo", "Correo Corporativo", "khalabyd@geoinfobusiness.cl", "Khalaby.2026", None),
        ("CRM", "CRM", "khalabyd@geoinfobusiness.cl", "Khalaby.2026", None),
        ("PC", "Sistemas", "Karina.halaby", "Geimser.2026", None),
        ("Vocalcom", "Telefonía", "K.halaby", "Kh.2026", "2018")
    ])
]

created = 0
for email, full_name, creds in users_data:
    user = db.query(User).filter(User.email == email).first()
    if not user:
        continue
    
    for sysLabel, category, username, password, url in creds:
        title = f"{sysLabel} - {full_name}"
        encrypted = encrypt_aes(password)
        
        # Check if exists
        existing = db.query(Credential).filter(
            Credential.owner_id == user.id,
            Credential.title == title,
            Credential.category == category
        ).first()
        
        if existing:
            existing.username = username
            existing.encrypted_password = encrypted
            existing.url = url
        else:
            new_cred = Credential(
                title=title,
                username=username,
                encrypted_password=encrypted,
                category=category,
                url=url,
                owner_id=user.id
            )
            db.add(new_cred)
            created += 1

db.commit()
print(f"Done. Fixed credentials: {created}")
