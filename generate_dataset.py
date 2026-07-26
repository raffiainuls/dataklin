import pandas as pd
import random
from faker import Faker
import datetime
from uuid import uuid4

# Setup Faker with Indonesian locale
fake = Faker('id_ID')

# Constants for edge cases
NUM_RECORDS = 500
DUPLICATE_RATE = 0.15 # 15% duplicates to test Entity Resolution
ANOMALY_RATE = 0.05   # 5% anomalous data for Outlier Detection

records = []
original_entities = []

print("Generating clean records...")
for _ in range(int(NUM_RECORDS * (1 - DUPLICATE_RATE))):
    customer_id = str(uuid4())[:8].upper()
    gender = random.choice(['M', 'F'])
    first_name = fake.first_name_male() if gender == 'M' else fake.first_name_female()
    last_name = fake.last_name()
    full_name = f"{first_name} {last_name}"
    
    # Generate realistic NIK (16 digits)
    nik = f"{random.randint(11, 99)}{random.randint(11, 99)}{random.randint(11, 99)}{fake.date_of_birth(minimum_age=18, maximum_age=65).strftime('%d%m%y')}{random.randint(1000, 9999)}"
    
    phone = fake.phone_number()
    email = f"{first_name.lower()}.{last_name.lower()}@{fake.free_email_domain()}"
    address = fake.address().replace('\n', ', ')
    city = fake.city()
    
    dob = fake.date_of_birth(minimum_age=18, maximum_age=65)
    join_date = fake.date_between(start_date='-5y', end_date='today')
    
    # Normal spending between 500k to 5M
    total_spending = random.randint(50, 500) * 10000 
    
    status = random.choice(['Active', 'Inactive', 'Suspended'])
    
    record = {
        'customer_id': customer_id,
        'nik': nik,
        'nama_lengkap': full_name,
        'email': email,
        'no_hp': phone,
        'alamat_domisili': address,
        'kota': city,
        'tanggal_lahir': dob.strftime('%Y-%m-%d'),
        'tanggal_bergabung': join_date.strftime('%Y-%m-%d'),
        'total_belanja': total_spending,
        'status_pelanggan': status
    }
    records.append(record)
    original_entities.append(record)

print("Injecting fuzzy duplicates (Entity Resolution testing)...")
# Introduce fuzzy duplicates for Entity Resolution (VD-301 & existing fuzzy match)
# We will create variations like typo in name, different email, same NIK but different phone, etc.
num_duplicates = int(NUM_RECORDS * DUPLICATE_RATE)
for _ in range(num_duplicates):
    base_record = random.choice(original_entities).copy()
    
    # Modify fields slightly to create "dirty" duplicates
    variation_type = random.choice(['name_typo', 'address_change', 'phone_format', 'all_different_but_nik'])
    
    if variation_type == 'name_typo':
        # E.g., Budi Santoso -> Budi S.
        parts = base_record['nama_lengkap'].split()
        if len(parts) > 1:
            base_record['nama_lengkap'] = f"{parts[0]} {parts[1][0]}."
    
    elif variation_type == 'address_change':
        # Same person, moved house
        base_record['alamat_domisili'] = fake.address().replace('\n', ', ')
        base_record['kota'] = fake.city()
        
    elif variation_type == 'phone_format':
        # Same phone, different format (0812 vs +62812 vs 62812)
        base_phone = base_record['no_hp']
        if base_phone.startswith('0'):
            base_record['no_hp'] = '+62' + base_phone[1:]
        elif base_phone.startswith('+62'):
            base_record['no_hp'] = '0' + base_phone[3:]
            
    elif variation_type == 'all_different_but_nik':
        # Person got married, changed last name, new email, new phone
        base_record['nama_lengkap'] = base_record['nama_lengkap'] + " (Baru)"
        base_record['email'] = f"baru.{base_record['email']}"
        base_record['no_hp'] = fake.phone_number()
        # NIK remains the exact same! This should cluster them.
        
    # Give it a new customer ID since it's from a "different system"
    base_record['customer_id'] = str(uuid4())[:8].upper()
    
    records.append(base_record)

print("Injecting anomalies and cross-column rule violations...")
# Introduce Anomalies and Format Errors
for _ in range(int(NUM_RECORDS * ANOMALY_RATE)):
    idx = random.randint(0, len(records) - 1)
    anomaly_type = random.choice(['extreme_outlier', 'cross_column_violation', 'bad_email', 'missing_values'])
    
    if anomaly_type == 'extreme_outlier':
        # Spendings usually 500k-5M. Make this one 99 Billion.
        records[idx]['total_belanja'] = 99000000000
    
    elif anomaly_type == 'cross_column_violation':
        # Join date BEFORE birth date (impossible)
        records[idx]['tanggal_bergabung'] = '1900-01-01'
        
    elif anomaly_type == 'bad_email':
        # Bad email format
        records[idx]['email'] = "not-an-email-at-all"
        
    elif anomaly_type == 'missing_values':
        records[idx]['nik'] = None
        records[idx]['no_hp'] = None

# Shuffle to mix duplicates and anomalies
random.shuffle(records)

# Convert to DataFrame and save
df = pd.DataFrame(records)
output_file = 'samples/dataklin_comprehensive_test.csv'
df.to_csv(output_file, index=False)

print(f"\nDataset generated successfully: {output_file}")
print(f"Total rows: {len(df)}")
print(f"Features ready to test:")
print("- Data Profiling & Type Inference")
print("- Rule Engine (Bad email, Date formats)")
print("- Cross-column Rule (Join date vs Birth date)")
print("- Outlier/Anomaly Detection (Extreme spending values)")
print("- PII Detection (NIK, Phone, Email, Name)")
print("- Entity Resolution (Semantic duplicates, typo names, changing address, same NIK)")
