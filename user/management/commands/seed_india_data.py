import os
import django
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Seed Indian states and cities into the database'

    def handle(self, *args, **options):
        from user.models import state, city

        INDIA_DATA = {
            "Andhra Pradesh": ["Visakhapatnam", "Vijayawada", "Guntur", "Nellore", "Tirupati", "Rajahmundry", "Kakinada", "Kurnool", "Anantapur", "Eluru"],
            "Arunachal Pradesh": ["Itanagar", "Naharlagun", "Tawang", "Ziro", "Pasighat", "Bomdila", "Along", "Tezu", "Roing", "Changlang"],
            "Assam": ["Guwahati", "Silchar", "Dibrugarh", "Jorhat", "Nagaon", "Tinsukia", "Tezpur", "Bongaigaon", "Dhubri", "Diphu"],
            "Bihar": ["Patna", "Gaya", "Bhagalpur", "Muzaffarpur", "Darbhanga", "Purnia", "Arrah", "Begusarai", "Katihar", "Munger"],
            "Chhattisgarh": ["Raipur", "Bhilai", "Bilaspur", "Korba", "Durg", "Rajnandgaon", "Jagdalpur", "Raigarh", "Ambikapur", "Mahasamund"],
            "Goa": ["Panaji", "Margao", "Vasco da Gama", "Mapusa", "Ponda", "Bicholim", "Curchorem", "Sanquelim", "Canacona", "Quepem"],
            "Gujarat": ["Ahmedabad", "Surat", "Vadodara", "Rajkot", "Bhavnagar", "Jamnagar", "Junagadh", "Gandhinagar", "Anand", "Nadiad", "Morbi", "Mehsana", "Bharuch", "Navsari", "Valsad"],
            "Haryana": ["Gurugram", "Faridabad", "Panipat", "Ambala", "Karnal", "Hisar", "Rohtak", "Sonipat", "Panchkula", "Yamunanagar"],
            "Himachal Pradesh": ["Shimla", "Dharamshala", "Mandi", "Solan", "Kullu", "Manali", "Hamirpur", "Una", "Bilaspur", "Chamba"],
            "Jharkhand": ["Ranchi", "Jamshedpur", "Dhanbad", "Bokaro", "Hazaribagh", "Deoghar", "Giridih", "Ramgarh", "Dumka", "Phusro"],
            "Karnataka": ["Bengaluru", "Mysuru", "Hubballi", "Mangaluru", "Belagavi", "Kalaburagi", "Davanagere", "Ballari", "Shivamogga", "Tumakuru"],
            "Kerala": ["Thiruvananthapuram", "Kochi", "Kozhikode", "Thrissur", "Kollam", "Kannur", "Alappuzha", "Palakkad", "Malappuram", "Kottayam"],
            "Madhya Pradesh": ["Bhopal", "Indore", "Jabalpur", "Gwalior", "Ujjain", "Sagar", "Dewas", "Satna", "Ratlam", "Rewa"],
            "Maharashtra": ["Mumbai", "Pune", "Nagpur", "Thane", "Nashik", "Aurangabad", "Solapur", "Kolhapur", "Amravati", "Navi Mumbai", "Sangli", "Jalgaon", "Akola", "Latur", "Ahmednagar"],
            "Manipur": ["Imphal", "Thoubal", "Bishnupur", "Churachandpur", "Kakching", "Senapati", "Ukhrul", "Tamenglong", "Chandel", "Jiribam"],
            "Meghalaya": ["Shillong", "Tura", "Jowai", "Nongstoin", "Williamnagar", "Baghmara", "Resubelpara", "Mairang", "Nongpoh", "Cherrapunji"],
            "Mizoram": ["Aizawl", "Lunglei", "Champhai", "Serchhip", "Kolasib", "Lawngtlai", "Mamit", "Saiha", "Hnahthial", "Saitual"],
            "Nagaland": ["Kohima", "Dimapur", "Mokokchung", "Tuensang", "Wokha", "Zunheboto", "Mon", "Phek", "Longleng", "Peren"],
            "Odisha": ["Bhubaneswar", "Cuttack", "Rourkela", "Berhampur", "Sambalpur", "Puri", "Balasore", "Baripada", "Bhadrak", "Jharsuguda"],
            "Punjab": ["Ludhiana", "Amritsar", "Jalandhar", "Patiala", "Bathinda", "Mohali", "Pathankot", "Hoshiarpur", "Batala", "Moga"],
            "Rajasthan": ["Jaipur", "Jodhpur", "Udaipur", "Kota", "Ajmer", "Bikaner", "Alwar", "Bhilwara", "Sikar", "Bharatpur"],
            "Sikkim": ["Gangtok", "Namchi", "Gyalshing", "Mangan", "Ravangla", "Singtam", "Rangpo", "Jorethang", "Nayabazar", "Yuksom"],
            "Tamil Nadu": ["Chennai", "Coimbatore", "Madurai", "Tiruchirappalli", "Salem", "Tirunelveli", "Erode", "Vellore", "Thoothukudi", "Dindigul"],
            "Telangana": ["Hyderabad", "Warangal", "Nizamabad", "Karimnagar", "Khammam", "Ramagundam", "Mahbubnagar", "Nalgonda", "Adilabad", "Suryapet"],
            "Tripura": ["Agartala", "Dharmanagar", "Udaipur", "Kailashahar", "Belonia", "Ambassa", "Khowai", "Sabroom", "Sonamura", "Kamalpur"],
            "Uttar Pradesh": ["Lucknow", "Kanpur", "Agra", "Varanasi", "Meerut", "Prayagraj", "Ghaziabad", "Noida", "Bareilly", "Aligarh", "Moradabad", "Gorakhpur", "Mathura", "Firozabad", "Jhansi"],
            "Uttarakhand": ["Dehradun", "Haridwar", "Rishikesh", "Haldwani", "Roorkee", "Kashipur", "Rudrapur", "Nainital", "Mussoorie", "Pithoragarh"],
            "West Bengal": ["Kolkata", "Howrah", "Durgapur", "Asansol", "Siliguri", "Bardhaman", "Malda", "Baharampur", "Habra", "Kharagpur"],
            "Andaman and Nicobar Islands": ["Port Blair", "Diglipur", "Rangat", "Mayabunder", "Bamboo Flat", "Garacharma", "Prothrapur", "Wandoor", "Car Nicobar", "Hut Bay"],
            "Chandigarh": ["Chandigarh"],
            "Dadra and Nagar Haveli and Daman and Diu": ["Silvassa", "Daman", "Diu"],
            "Delhi": ["New Delhi", "Delhi", "Dwarka", "Rohini", "Saket", "Lajpat Nagar", "Karol Bagh", "Connaught Place", "Chandni Chowk", "Janakpuri"],
            "Jammu and Kashmir": ["Srinagar", "Jammu", "Anantnag", "Baramulla", "Sopore", "Kathua", "Udhampur", "Rajouri", "Poonch", "Kupwara"],
            "Ladakh": ["Leh", "Kargil"],
            "Lakshadweep": ["Kavaratti", "Agatti", "Minicoy", "Amini", "Andrott"],
            "Puducherry": ["Puducherry", "Karaikal", "Mahe", "Yanam"],
        }

        created_states = 0
        created_cities = 0

        for state_name, cities_list in INDIA_DATA.items():
            s, s_created = state.objects.get_or_create(statename=state_name)
            if s_created:
                created_states += 1

            for city_name in cities_list:
                _, c_created = city.objects.get_or_create(cityname=city_name, stateid=s)
                if c_created:
                    created_cities += 1

        self.stdout.write(self.style.SUCCESS(
            f'Successfully seeded {created_states} states and {created_cities} cities.'
        ))
