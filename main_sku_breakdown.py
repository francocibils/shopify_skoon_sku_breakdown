import pandas as pd
import streamlit as st

from io import BytesIO
from xlsxwriter import Workbook
from helper_functions import *

st.title('Shopify - Skoon SKU breakdown')
st.header('File upload')
st.markdown('Upload file to obtain gifts, free-reships and coupons.')

raw = st.file_uploader('Upload Shopify file', type = ['xlsx', 'xls', 'csv'])

sku_list = {
    '400-002-177': 'Bag 8 lb',
    '400-002-178': 'Bag 4 lb',
    '400-002-180': 'Box 4 lb * 2',
    '400-002-332': 'Bag 8 lb Lavender',
    '400-002-333': 'Bag 8 lb Lemon',
    '400-002-334': 'Bag 8 lb FineG',
    '400-002-335': 'Box 6 lb'
}

if raw is not None:
    file_type = get_file_type(raw)
    
    if file_type == 'csv':
        raw_df = pd.read_csv(raw)
    elif file_type == 'xlsx' or file_type == 'xls':
        raw_df = pd.read_excel(raw)
    
    st.success('Shopify file uploaded successfully.')

if st.button('Process file'):

    keep_cols = ['Created at', 'Subtotal', 'Lineitem quantity', 'Lineitem sku', 'Tags']
    df = raw_df[keep_cols]
    df = df[df['Subtotal'] > 0]

    df['Date'] = pd.to_datetime(df['Created at']).dt.strftime('%Y-%m-%d')
    df['Tags_mapped'] = df['Tags'].apply(map_value)
    df = df[df['Lineitem sku'].isin(sku_list.keys())]
    df['SKU_name'] = df['Lineitem sku'].map(sku_list)

    fechas = df['Date'].unique()
    tags = df['Tags_mapped'].unique()
    skus = df['SKU_name'].unique()

    combinaciones = pd.MultiIndex.from_product(
        [fechas, tags, skus],
        names = ['Date', 'Tags_mapped', 'SKU_name']
    )

    agg_df = df.groupby(['Date', 'Tags_mapped', 'SKU_name']).agg(
        Quantity = ('Lineitem quantity', 'count'),
        Item_quantity = ('Lineitem quantity', 'sum'),
        Subtotal = ('Subtotal', 'sum')
    )
    agg_df = agg_df.reindex(combinaciones, fill_value = 0).reset_index()

    # Crear la tabla pivot
    pivoted_df = agg_df.pivot_table(
        index = 'Date',
        columns = ['Tags_mapped', 'SKU_name'],
        values = ['Quantity', 'Item_quantity', 'Subtotal'],
        fill_value = 0
    )

    # Ordenar los niveles de columnas (primero Tags_mapped, luego SKU_name)
    pivoted_df = pivoted_df.sort_index(axis = 1, level = [1, 2])

    # Aplanar MultiIndex en las columnas
    pivoted_df.columns = [
        f"{tag}_{sku}_{metric}"
        for metric, tag, sku in pivoted_df.columns
    ]

    pivoted_df = pivoted_df.reset_index()

    st.success('Shopify file has been processed successfully.')

    output = BytesIO()
    with pd.ExcelWriter(output, engine = 'xlsxwriter') as writer:
        pivoted_df.to_excel(writer, index = False, sheet_name = 'SKU breakdown')
        writer.close()

        # Rewind the buffer
        output.seek(0)

        # Create a download button
        st.download_button(
            label = "Download Excel file",
            data = output,
            file_name = "Shopify - Skoon.xlsx",
            mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
