import pandas as pd
import unicodedata
 

recife = ['AFLITOS', 'AFOGADOS', 'ALTO DO MANDU', 'ALTO JOSÉ BONIFÁCIO',
       'ALTO JOSÉ DO PINHO', 'ALTO SANTA TEREZINHA', 'APIPUCOS', 'AREIAS',
       'ARRUDA', 'BARRO', 'BEBERIBE', 'BOA VIAGEM', 'BOA VISTA',
       'BOMBA DO HEMETÉRIO', 'BONGI', 'BRASÍLIA TEIMOSA',
       'BREJO DA GUABIRABA', 'BREJO DE BEBERIBE', 'CABANGA', 'CAJUEIRO',
       'CAMPINA DO BARRETO', 'CAMPO GRANDE', 'CASA AMARELA', 'CASA FORTE',
       'CAXANGÁ', 'CAÇOTE', 'CIDADE UNIVERSITÁRIA', 'COELHOS',
       'COQUEIRAL', 'CORDEIRO', 'CURADO', 'CÓRREGO DO JENIPAPO', 'DERBY',
       'DOIS IRMÃOS', 'DOIS UNIDOS', 'ENCRUZILHADA', 'ENGENHO DO MEIO',
       'ESPINHEIRO', 'ESTÂNCIA', 'FUNDÃO', 'GRAÇAS', 'GUABIRABA',
       'HIPÓDROMO', 'IBURA', 'ILHA DO LEITE', 'ILHA DO RETIRO',
       'ILHA JOANA BEZERRA', 'IMBIRIBEIRA', 'IPSEP', 'IPUTINGA',
       'JAQUEIRA', 'JARDIM SÃO PAULO', 'JIQUIÁ', 'JORDÃO',
       'LINHA DO TIRO', 'MACAXEIRA', 'MADALENA', 'MANGABEIRA',
       'MANGUEIRA', 'MONTEIRO', 'MORRO DA CONCEIÇÃO', 'MUSTARDINHA',
       'NOVA DESCOBERTA', 'PAISSANDU', 'PARNAMIRIM', 'PASSARINHO',
       'PEIXINHOS', 'PINA', 'PONTO DE PARADA', 'PORTO DA MADEIRA', 'POÇO',
       'PRADO', 'RECIFE', 'ROSARINHO', 'SAN MARTIN', 'SANCHO', 'SANTANA',
       'SANTO AMARO', 'SANTO ANTÔNIO', 'SOLEDADE', 'SÃO JOSÉ',
       'TAMARINEIRA', 'TEJIPIÓ', 'TORRE', 'TORREÃO', 'TORRÕES', 'TOTÓ',
       'VASCO DA GAMA', 'VÁRZEA', 'ZUMBI', 'ÁGUA FRIA']

def colgate(df):
    df['Bairro'] = df['Bairro'].apply(limpar_acento).str.upper()
    df = df.query("Bairro in @recife")
    df['Estilo'] = df['Estilo'].map(dic_sic_cad)
    df['ano'] = pd.to_numeric(df['ano'], errors='coerce')
    df['ano'] = pd.to_datetime(df['ano'], unit='D', origin='1899-12-30')
    df['ano'] = df['ano'].dt.year
    df = df.groupby(["Estilo","Bairro",'ano'],as_index=False)['valor'].sum().reset_index()
    df = df.sort_values(by='ano', ascending=False)
    
    return df

def limpar_acento(txt):
    if pd.isnull(txt):
        return txt
    txt = ''.join(ch for ch in unicodedata.normalize('NFKD', txt) 
        if not unicodedata.combining(ch))
    return txt


dic_sic_cad = {
    'Fotografia': 'Fotografia',
    'nan': 'Outros',
 'Audiovisual':'Audiovisual' ,
 'Cultura Popular': 'Cultura Popular',
 'Artes Visuais': 'Artes Visuais',
 'Música': 'Música',
 'Literatura':'Literatura' ,
 'Pesquisa E Formação Cultural':'Pesquisa e Formação' ,
 'Design E Moda': 'Moda',
 'Dança': 'Dança',
 'Artesanato': 'Artesanato' ,
 'Patrimônio Cultural E Museologia':'Patrimonio' ,
 'Teatro':'Artes cenicas' ,
 'Artes Culturais Integradas E Arte E Tecnologia':'Artes Integradas' ,
 'Circo': 'Circo',
 'Artes Plásticas E Gráficas': 'Artes Visuais' ,
 'Opera': 'Opera',
 'Gastronomia':'Gastronomia' ,
    
}