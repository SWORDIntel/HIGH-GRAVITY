#!/bin/bash
# Monitor Phoenix Video Generation Job

OPERATION="models/veo-3.1-generate-preview/operations/e28anf7mnneo"
API_KEY="AIzaSyD0A0rw0QD0iVkVb7EJnD_AKVU5Lv4ryQw"
OUTPUT_DIR="veo3_outputs"

mkdir -p "$OUTPUT_DIR"

echo "======================================================================="
echo "MONITORING VEO 3.1 VIDEO GENERATION"
echo "======================================================================="
echo "Operation: $OPERATION"
echo "Output: $OUTPUT_DIR/phoenix_operation_phoenix.mp4"
echo "======================================================================="
echo ""

while true; do
    echo "[*] Checking status... ($(date '+%H:%M:%S'))"
    
    RESPONSE=$(curl -s "https://generativelanguage.googleapis.com/v1beta/$OPERATION?key=$API_KEY")
    
    # Check if done
    DONE=$(echo "$RESPONSE" | python3 -c "import json, sys; data=json.load(sys.stdin); print(data.get('done', False))" 2>/dev/null)
    
    if [ "$DONE" = "True" ]; then
        echo "[+] Video generation complete!"
        echo ""
        
        # Check for error
        ERROR=$(echo "$RESPONSE" | python3 -c "import json, sys; data=json.load(sys.stdin); print('error' in data)" 2>/dev/null)
        
        if [ "$ERROR" = "True" ]; then
            echo "[!] Generation failed:"
            echo "$RESPONSE" | python3 -m json.tool
            exit 1
        fi
        
        # Extract file URI
        FILE_URI=$(echo "$RESPONSE" | python3 -c "
import json, sys
data = json.load(sys.stdin)
response = data.get('response', {})
predictions = response.get('predictions', [])
if predictions:
    file_data = predictions[0].get('bytesBase64Encoded')
    if not file_data:
        # Try alternate structure
        for key in ['videoUri', 'uri', 'fileUri']:
            if key in predictions[0]:
                print(predictions[0][key])
                break
" 2>/dev/null)
        
        if [ -z "$FILE_URI" ]; then
            echo "[!] Could not extract file URI"
            echo "$RESPONSE" | python3 -m json.tool
            exit 1
        fi
        
        echo "[*] File URI: $FILE_URI"
        echo "[*] Downloading video..."
        
        # Download video
        curl -s "${FILE_URI}?key=${API_KEY}" -o "$OUTPUT_DIR/phoenix_operation_phoenix.mp4"
        
        if [ -f "$OUTPUT_DIR/phoenix_operation_phoenix.mp4" ]; then
            SIZE=$(ls -lh "$OUTPUT_DIR/phoenix_operation_phoenix.mp4" | awk '{print $5}')
            echo "[+] Downloaded: $OUTPUT_DIR/phoenix_operation_phoenix.mp4 ($SIZE)"
            echo ""
            echo "======================================================================="
            echo "VIDEO GENERATION COMPLETE"
            echo "======================================================================="
            exit 0
        else
            echo "[!] Download failed"
            exit 1
        fi
    fi
    
    echo "    Status: Processing..."
    echo "    Waiting 30s before next check..."
    echo ""
    sleep 30
done
