# import curl

# curl https://newsapi.org/v2/everything -G \
#     -d q=Apple \
#     -d from=2023-09-02 \
#     -d sortBy=popularity \
#     -d apiKey=API_KEY

# https://newsapi.org/v2/everything?q=Apple&from=2023-09-02&sortBy=popularity&apiKey=



# import requests


# url = ('https://newsapi.org/v2/everything?'
#        'from=2023-09-01&'
#        'sortBy=popularity&'
#        'page=1&'
#        'pageSize=30&'
#        'sources=wired&'
#        'apiKey=a63ecd28659a498c9f70555ad0396ecb')
# r = requests.get(url, allow_redirects=True)

# open('Test.json', 'wb').write(r.content)
# print(r.json())

num = 0x222222

num_int = int(int(str(num)[2:]),16)

red = (num_int >> 16) & 0xFF
green = (num_int >> 8) & 0xFF
blue = num_int & 0xFF

factor = 1

red = max(0, red - int(255 * factor))
green = max(0, green - int(255 * factor))
blue = max(0, blue - int(255 * factor))

reduced_color_int = (red << 16) | (green << 8) | blue

    # Convert the new color integer back to a hex color
reduced_color = "#{:06X}".format(reduced_color_int)

print(reduced_color)