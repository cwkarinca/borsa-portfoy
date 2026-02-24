import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import yfinance as yf

# --- AYARLAR ---
st.set_page_config(page_title="Portföy Defterim (Bulut)", layout="wide")

# Google Sheets Bağlantısı
# ÖNEMLİ: Linkini buraya yapıştır
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1U-WWydW9YJSj_14iQNp4msEpYS2Ireh1lyKa6_D3Drk/edit?usp=sharing"

conn = st.connection("gsheets", type=GSheetsConnection)

def verileri_cek():
    try:
        return conn.read(spreadsheet=SPREADSHEET_URL, ttl=0)
    except:
        # Eğer tablo boşsa başlıklarla yeni bir tane oluşturur
        return pd.DataFrame(columns=["Tarih", "Portföy", "Tip", "Hisse", "Adet", "Fiyat", "Toplam"])

# --- GİRİŞ KONTROLÜ ---
if 'auth' not in st.session_state: st.session_state['auth'] = False

if not st.session_state['auth']:
    st.title("🔐 Portföy Girişi")
    u = st.text_input("Kullanıcı")
    p = st.text_input("Şifre", type="password")
    if st.button("Giriş"):
        if u == "admin" and p == "1234":
            st.session_state['auth'] = True
            st.rerun()
else:
    menu = ["📈 Portföy Analizi", "➕ Yeni İşlem Ekle", "📜 Hisse Bazlı İşlem Defteri"]
    choice = st.sidebar.selectbox("Menü", menu)
    
    df = verileri_cek()

    if choice == "➕ Yeni İşlem Ekle":
        st.header("➕ Yeni İşlem Kaydet")
        with st.form("yeni_ekle"):
            c1, c2 = st.columns(2)
            tarih = c1.date_input("Tarih", datetime.now())
            tip = c1.selectbox("İşlem Tipi", ["Alış", "Satış"])
            hisse = c1.text_input("Hisse Kodu (Örn: TOASO)").upper()
            p_ismi = c2.selectbox("Portföy", ["Temettü", "Büyüme", "Altın/Emtia"])
            adet = c2.number_input("Adet", min_value=0.0001, format="%.4f")
            fiyat = c2.number_input("Fiyat", min_value=0.01, format="%.2f")
            
            if st.form_submit_button("Google Tabloya Kaydet"):
                yeni_veri = pd.DataFrame([{
                    "Tarih": tarih.strftime('%Y-%m-%d'),
                    "Portföy": p_ismi,
                    "Tip": tip,
                    "Hisse": hisse,
                    "Adet": adet,
                    "Fiyat": fiyat,
                    "Toplam": adet * fiyat
                }])
                guncel_df = pd.concat([df, yeni_veri], ignore_index=True)
                conn.update(spreadsheet=SPREADSHEET_URL, data=guncel_df)
                st.success("Veri Google Tabloya işlendi!")
                st.rerun()

    elif choice == "📜 Hisse Bazlı İşlem Defteri":
        st.header("📜 Hisse Bazlı Gruplandırılmış İşlemler")
        if not df.empty:
            df['Tarih'] = pd.to_datetime(df['Tarih'])
            df = df.sort_values(by=["Hisse", "Tarih"], ascending=[True, True])
            
            for h_ad in df['Hisse'].unique():
                with st.expander(f"📂 {h_ad} İşlemleri", expanded=True):
                    h_df = df[df['Hisse'] == h_ad]
                    st.dataframe(h_df[["Tarih", "Tip", "Adet", "Fiyat", "Toplam"]], use_container_width=True, hide_index=True)
                    
                    if st.button(f"{h_ad} Satırını Sil (Son İşlem)", key=f"del_{h_ad}"):
                        guncel_df = df.drop(h_df.index[-1])
                        conn.update(spreadsheet=SPREADSHEET_URL, data=guncel_df)
                        st.rerun()
        else:
            st.info("Tablo henüz boş.")

    elif choice == "📈 Portföy Analizi":
        st.header("📊 Güncel Durum Analizi")
        if not df.empty:
            # Analiz kodları buraya gelecek (Daha önceki analiz mantığıyla aynı)
            st.write("Veriler Google Sheets üzerinden başarıyla okunuyor.")
            st.dataframe(df)
