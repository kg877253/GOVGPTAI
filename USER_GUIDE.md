# GovGPT User Guide

## What Questions Can You Ask GovGPT?

GovGPT is designed to generate RTI (Right to Information) applications for Indian government schemes and services. You can ask about:

### **Supported Government Schemes:**
- **PM-KISAN**: "My PM-KISAN installment not received for last 3 months"
- **Ration/PDS**: "Fair Price Shop dealer not giving ration for past 2 months"
- **Pension**: "Old age pension stopped without any reason"
- **Ayushman Bharat**: "Ayushman card not generated despite application"
- **PM Awas Yojana**: "PM Awas allotment status not received"
- **General Schemes**: Any government scheme or benefit-related issue

### **How to Ask Questions:**

**Format:**
```
Name: [Your Full Name]
Address: [Complete Address with District/State]
Problem: [Describe your issue in detail]
```

**Example Questions:**
1. "Hamare Fair Price Shop dealer ne pichle 2 mahine se ration card par chawal aur gehu dene se mana kar diya hai."
2. "PM-KISAN ka 15th installment mere account mein nahi aaya, status check karna hai."
3. "Mere pension ka payment 6 mahine se ruka hua hai, koi reason nahi diya gaya."
4. "Ayushman Bharat card ka application 3 mahine pehle kiya par abhi tak card nahi mila."
5. "PM Awas Yojana mein form bhara tha par koi acknowledge nahi mila."

### **Language Support:**
- **Hindi**: You can write in Hindi (Devanagari or Roman script)
- **English**: You can write in English
- **Mixed**: You can use Hinglish (Hindi written in English)

## Constraints & Limitations

### **What GovGPT CANNOT Do:**
- ❌ Cannot file the RTI application for you (you must submit it yourself)
- ❌ Cannot provide legal advice beyond RTI drafting
- ❌ Cannot access real-time government databases
- ❌ Cannot guarantee government response
- ❌ Cannot handle personal disputes (non-government matters)
- ❌ Cannot generate RTI for private companies
- ❌ Cannot create fake or fraudulent applications
- ❌ Cannot bypass government procedures

### **What GovGpt CAN Do:**
- ✅ Generate professional RTI applications
- ✅ Auto-detect relevant government departments
- ✅ Fill in your address automatically
- ✅ Create legally correct RTI format
- ✅ Generate downloadable PDF
- ✅ Support Hindi and English
- ✅ Work with government scheme information
- ✅ Provide ready-to-submit RTI letters

### **Required Information:**
1. **Full Name**: Complete legal name as per documents
2. **Complete Address**: Must include District and State for department detection
3. **Specific Problem**: Clear description of the issue
4. **Scheme Name**: If applicable, mention the specific scheme

### **Address Format for Best Results:**
```
Good: "Village XYZ, District Pali, Rajasthan"
Bad: "Pali, Rajasthan"
Best: "Gram Panchayat Bilara, District Pali, Rajasthan 306001"
```

## How to Use GovGPT

### **Step 1: Open Application**
- Go to http://localhost:5000
- Wait for the page to load

### **Step 2: Fill Your Information**
- **Name**: Enter your full name
- **Address**: Enter complete address with district
- **Problem**: Describe your issue in detail

### **Step 3: Generate RTI**
- Click "Generate RTI Application"
- Wait for AI to process (may take 10-30 seconds)
- Review the generated RTI

### **Step 4: Download PDF**
- Click "Download PDF" button
- PDF will be saved with your name and date
- Print the PDF

### **Step 5: Submit RTI**
- Attach Rs. 10 IPO/DD/Online payment proof
- Sign the application
- Submit to the addressed department
- Keep copy for your records

## Current Status

### **API Status:**
- **Gemini API**: Quota exhausted (using fallback)
- **Groq API**: Ready (free alternative)
- **Fallback System**: Active and working

### **Auto-Fill Features:**
- ✅ Address extraction from input
- ✅ Department detection based on problem
- ✅ District/block extraction from address
- ✅ Scheme-specific question generation
- ✅ Professional RTI formatting

## Tips for Best Results

1. **Be Specific**: "Ration not given" is better than "Problem with ration"
2. **Include Dates**: "Not received since March 2025" helps
3. **Mention Scheme**: Always specify which scheme you're asking about
4. **Complete Address**: Include district for proper department routing
5. **Use Simple Language**: Clear and direct questions work best

## Troubleshooting

### **PDF Shows Wrong Content:**
- Refresh the page and regenerate RTI
- Check browser console for errors
- Ensure JavaScript is enabled

### **Department Not Detected:**
- Include district name in address
- Mention specific scheme name in problem
- Try using English if Hindi detection fails

### **Generation Takes Too Long:**
- Check internet connection
- API quota may be exhausted (using fallback)
- Try again after a few minutes

## Support

For issues or questions:
- Check the logs in terminal
- Ensure all dependencies are installed
- Verify API keys are configured correctly
