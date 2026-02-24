import streamlit as st
import pandas as pd
import sqlite3
import yfinance as yf
from datetime import datetime

# --- VERİTABANI ---
def init_db():
    conn = sqlite3.connect('borsa_portfoy.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS islemler
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  tarih TEXT, portfoy_ismi TEXT, islem_tipi TEXT, hisse_kodu TEXT, 
                  adet REAL, fiyat REAL, toplam_tutar REAL)''')
    conn.commit()
    conn.close()

def veri_islem(islem_id, tarih, p_ismi, tip, hisse, adet, fiyat, mod="ekle"):
    conn = sqlite3.connect('borsa_portfoy.db')
    c = conn.cursor()
    hisse_temiz = hisse.upper().replace(".", "").strip()
    islem_adedi = -abs(adet) if tip == "Satış" else abs(adet)
    toplam = islem_adedi * fiyat
    
    if mod == "ekle":
        c.execute("INSERT INTO islemler (tarih, portfoy_ismi, islem_tipi, hisse_kodu, adet, fiyat, toplam_tutar) VALUES (?,?,?,?,?,?,?)",
                  (tarih, p_ismi, tip, hisse_temiz, islem_adedi, fiyat, toplam))
    elif mod == "guncelle":
        c.execute("""UPDATE islemler SET tarih=?, portfoy_ismi=?, islem_tipi=?, hisse_kodu=?, adet=?, fiyat=?, toplam_tutar=? 
                     WHERE id=?""", (tarih, p_ismi, tip, hisse_temiz, islem_adedi, fiyat, toplam, islem_id))
    conn.commit()
    conn.close()

def kayit_sil(id):
    conn = sqlite3.connect('borsa_portfoy.db')
    c = conn.cursor()
    c.execute("DELETE FROM islemler WHERE id=?", (id,))
    conn.commit()
    conn.close()

# --- UYGULAMA ---
st.set_page_config(page_title="Hisse Bazlı Portföy", layout="wide")
init_db()

if 'auth' not in st.session_state: st.session_state['auth'] = False

if not st.session_state['auth']:
    st.title("🔐 Giriş")
    u = st.text_input("Kullanıcı")
    p = st.text_input("Şifre", type="password")
    if st.button("Giriş"):
        if u == "admin" and p == "1234":
            st.session_state['auth'] = True
            st.rerun()
else:
    menu = ["📈 Portföy Analizi", "➕ Yeni İşlem Ekle", "📜 Hisse Bazlı İşlem Defteri"]
    choice = st.sidebar.selectbox("Menü", menu)

    conn = sqlite3.connect('borsa_portfoy.db')
    df = pd.read_sql_query("SELECT * FROM islemler", conn)
    conn.close()

    if choice == "➕ Yeni İşlem Ekle":
        st.header("➕ Yeni İşlem Kaydet")
        with st.form("yeni_ekle"):
            c1, c2 = st.columns(2)
            tarih = c1.date_input("Tarih", datetime.now())
            tip = c1.selectbox("İşlem Tipi", ["Alış", "Satış"])
            hisse = c1.text_input("Hisse Kodu (Örn: TOASO)")
            p_ismi = c2.selectbox("Portföy", ["Temettü", "Büyüme", "Altın/Emtia"])
            adet = c2.number_input("Adet", min_value=0.0001, format="%.4f")
            fiyat = c2.number_input("Birim Fiyat (TL)", min_value=0.01, format="%.2f")
            if st.form_submit_button("Deftere Kaydet"):
                veri_islem(None, tarih, p_ismi, tip, hisse, adet, fiyat, mod="ekle")
                st.success("Kayıt Başarılı!")
                st.rerun()

    elif choice == "📜 Hisse Bazlı İşlem Defteri":
        st.header("📜 Hisse Bazlı Gruplandırılmış İşlemler")
        if not df.empty:
            df['tarih'] = pd.to_datetime(df['tarih'])
            # Önce Hisse Adına, sonra Tarihe göre sıralıyoruz (Gruplama için)
            df = df.sort_values(by=["hisse_kodu", "tarih"], ascending=[True, True])

            hisseler = df['hisse_kodu'].unique()
            
            for h_ad in hisseler:
                with st.expander(f"📂 {h_ad} İşlemleri", expanded=True):
                    hisse_df = df[df['hisse_kodu'] == h_ad]
                    
                    # Başlıklar
                    header_cols = st.columns([1.5, 1, 1, 1, 1.5, 1, 1])
                    labels = ["Tarih", "Tip", "Adet", "Fiyat", "Toplam Tutar", "Düzenle", "Sil"]
                    for col, label in zip(header_cols, labels):
                        col.write(f"**{label}**")
                    
                    for i, row in hisse_df.iterrows():
                        r_col = st.columns([1.5, 1, 1, 1, 1.5, 1, 1])
                        r_col[0].write(row['tarih'].strftime('%d-%m-%Y'))
                        r_col[1].write(row['islem_tipi'])
                        r_col[2].write(f"{abs(row['adet']):.2f}")
                        r_col[3].write(f"{row['fiyat']:.2f} TL")
                        r_col[4].write(f"{abs(row['toplam_tutar']):.2f} TL")
                        
                        # DÜZENLEME
                        with r_col[5].popover("📝"):
                            st.write(f"### {h_ad} Kaydını Düzenle")
                            e_tar = st.date_input("Tarih", row['tarih'], key=f"et_{row['id']}")
                            e_tip = st.selectbox("Tip", ["Alış", "Satış"], index=0 if row['islem_tipi']=="Alış" else 1, key=f"etip_{row['id']}")
                            e_adet = st.number_input("Adet", value=abs(row['adet']), key=f"ea_{row['id']}")
                            e_fiyat = st.number_input("Fiyat", value=row['fiyat'], key=f"ef_{row['id']}")
                            if st.button("Güncelle", key=f"eb_{row['id']}", use_container_width=True):
                                veri_islem(row['id'], e_tar, row['portfoy_ismi'], e_tip, h_ad, e_adet, e_fiyat, mod="guncelle")
                                st.rerun()

                        # SİLME
                        if r_col[6].button("🗑️", key=f"ed_{row['id']}"):
                            kayit_sil(row['id'])
                            st.rerun()
        else:
            st.info("Defterde henüz kayıt yok.")

    elif choice == "📈 Portföy Analizi":
        st.header("📊 Güncel Durum Analizi")
        if not df.empty:
            ozet = df.groupby('hisse_kodu').agg({'adet': 'sum', 'toplam_tutar': 'sum'}).reset_index()
            ozet = ozet[ozet['adet'] > 0.0001]

            if not ozet.empty:
                guncel_fiyatlar = {}
                for h in ozet['hisse_kodu']:
                    try:
                        tick = yf.Ticker(f"{h}.IS")
                        hist = tick.history(period="1d")
                        guncel_fiyatlar[h] = hist['Close'].iloc[-1] if not hist.empty else 0
                    except: guncel_fiyatlar[h] = 0

                ozet['Güncel Fiyat'] = ozet['hisse_kodu'].map(guncel_fiyatlar)
                
                # Manuel fiyat sigortası
                if 0 in ozet['Güncel Fiyat'].values:
                    st.warning("Bazı fiyatlar alınamadı. Lütfen manuel girin:")
                    for idx, r in ozet[ozet['Güncel Fiyat'] == 0].iterrows():
                        ozet.at[idx, 'Güncel Fiyat'] = st.number_input(f"{r['hisse_kodu']} Güncel Fiyat", key=f"m_{idx}")

                ozet['Maliyet'] = ozet['toplam_tutar']
                ozet['Değer'] = ozet['adet'] * ozet['Güncel Fiyat']
                ozet['K/Z'] = ozet['Değer'] - ozet['Maliyet']
                
                t_m = ozet['Maliyet'].sum()
                t_d = ozet['Değer'].sum()
                t_kz = t_d - t_m

                c1, c2, c3 = st.columns(3)
                c1.metric("Toplam Alış", f"{t_m:,.2f} TL")
                c2.metric("Güncel Değer", f"{t_d:,.2f} TL")
                c3.metric("Net Kar/Zarar", f"{t_kz:,.2f} TL", f"%{(t_kz/t_m*100):.2f}")

                st.dataframe(ozet.style.format({
                    'adet': '{:.2f}', 'Maliyet': '{:.2f} TL', 'Güncel Fiyat': '{:.2f} TL',
                    'Değer': '{:.2f} TL', 'K/Z': '{:.2f} TL'
                }), use_container_width=True)