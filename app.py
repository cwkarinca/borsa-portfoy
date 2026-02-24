import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import yfinance as yf

# --- AYARLAR ---
st.set_page_config(page_title="Hisse Bazlı Portföy", layout="wide")

# Google Sheets Bağlantısı
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1U-WWydW9YJSj_14iQNp4msEpYS2Ireh1lyKa6_D3Drk/edit?usp=sharing"
conn = st.connection("gsheets", type=GSheetsConnection)

def verileri_cek():
    try:
        return conn.read(spreadsheet=SPREADSHEET_URL, ttl=0)
    except:
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
                st.success("Veri Kaydedildi!")
                st.rerun()

    elif choice == "📜 Hisse Bazlı İşlem Defteri":
        st.header("📜 İşlem Defteri")
        if not df.empty:
            df['Tarih'] = pd.to_datetime(df['Tarih'])
            df = df.sort_values(by=["Hisse", "Tarih"], ascending=[True, True])
            
            for h_ad in df['Hisse'].unique():
                with st.expander(f"📂 {h_ad} İşlemleri", expanded=True):
                    h_df = df[df['Hisse'] == h_ad]
                    st.dataframe(h_df[["Tarih", "Tip", "Adet", "Fiyat", "Toplam"]], use_container_width=True, hide_index=True)
                    
                    if st.button(f"{h_ad} Son İşlemi Sil", key=f"del_{h_ad}"):
                        guncel_df = df.drop(h_df.index[-1])
                        conn.update(spreadsheet=SPREADSHEET_URL, data=guncel_df)
                        st.rerun()
        else:
            st.info("Tablo henüz boş.")

    elif choice == "📈 Portföy Analizi":
        st.header("📊 Güncel Durum")
        if not df.empty:
            # Alış/Satış adetlerini ve maliyetleri hesapla
            df['Net_Adet'] = df.apply(lambda x: x['Adet'] if x['Tip'] == "Alış" else -x['Adet'], axis=1)
            df['Net_Tutar'] = df.apply(lambda x: x['Toplam'] if x['Tip'] == "Alış" else -x['Toplam'], axis=1)
            
            ozet = df.groupby('Hisse').agg({'Net_Adet': 'sum', 'Net_Tutar': 'sum'}).reset_index()
            ozet = ozet[ozet['Net_Adet'] > 0.0001]

            if not ozet.empty:
                guncel_fiyatlar = {}
                with st.spinner("Fiyatlar çekiliyor..."):
                    for h in ozet['Hisse']:
                        try:
                            tick = yf.Ticker(f"{h}.IS")
                            f = tick.history(period="1d")['Close'].iloc[-1]
                            guncel_fiyatlar[h] = f
                        except: guncel_fiyatlar[h] = 0

                ozet['Güncel Fiyat'] = ozet['Hisse'].map(guncel_fiyatlar)
                ozet['Maliyet'] = ozet['Net_Tutar']
                ozet['Değer'] = ozet['Net_Adet'] * ozet['Güncel Fiyat']
                ozet['K/Z'] = ozet['Değer'] - ozet['Maliyet']
                
                c1, c2, c3 = st.columns(3)
                c1.metric("Toplam Maliyet", f"{ozet['Maliyet'].sum():,.2f} TL")
                c2.metric("Güncel Değer", f"{ozet['Değer'].sum():,.2f} TL")
                kz_toplam = ozet['K/Z'].sum()
                c3.metric("Net Kar/Zarar", f"{kz_toplam:,.2f} TL")

                st.dataframe(ozet, use_container_width=True)
        else:
            st.info("Analiz için veri bulunamadı.")
