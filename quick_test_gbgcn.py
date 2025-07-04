#!/usr/bin/env python3
import requests

BASE_URL = 'http://localhost:8000'
API_BASE = f'{BASE_URL}/api/v1'

print(' PROBANDO MODELO GBGCN')
print('='*50)

login_data = {'username': 'test@example.com', 'password': 'testpassword123'}
response = requests.post(f'{API_BASE}/login', data=login_data)

if response.status_code == 200:
    token = response.json()['access_token']
    headers = {'Authorization': f'Bearer {token}'}
    print(' Autenticado exitosamente')
    
    # Recomendaciones
    print('\n RECOMENDACIONES GBGCN:')
    rec_response = requests.get(f'{API_BASE}/recommendations/', headers=headers)
    
    if rec_response.status_code == 200:
        recommendations = rec_response.json()
        print(f' {len(recommendations)} recomendaciones')
        
        for i, rec in enumerate(recommendations[:3], 1):
            print(f'{i}. {rec.get(\
item_name\, \Item\)} - Score: {rec.get(\recommendation_score\, 0):.3f}')
    else:
        print(f' Error: {rec_response.status_code}')
    
    # Grupos
    print('\n GRUPOS:')
    groups_response = requests.get(f'{API_BASE}/groups/', headers=headers)
    
    if groups_response.status_code == 200:
        groups = groups_response.json()
        print(f' {len(groups)} grupos encontrados')
        
        for i, group in enumerate(groups[:3], 1):
            print(f'{i}. {group.get(\title\, \Grupo\)} - ')
    else:
        print(f' Error: {groups_response.status_code}')
        
    print('\n MODELO GBGCN FUNCIONANDO!')
    
else:
    print(f' Error login: {response.status_code}')

