import os
import re

footer_scripts = """  <!-- scripts -->
  <script src="{% static 'assets/js/jquery-3.7.1.js' %}"></script>
  <script src="{% static 'assets/js/bootstrap.bundle.min.js' %}"></script>
  <script src="{% static 'assets/js/aos.js' %}"></script>
  <script src="{% static 'assets/js/menu/menu.js' %}"></script>
  <script src="{% static 'assets/js/isotope.pkgd.min.js' %}"></script>
  <script src="{% static 'assets/js/jquery.magnific-popup.min.js' %}"></script>
  <script src="{% static 'assets/js/swiper-bundle.min.js' %}"></script>
  <script src="{% static 'assets/js/countdown.js' %}"></script>
  <script src="{% static 'assets/js/slick.js' %}"></script>
  <script src="{% static 'assets/js/wow.min.js' %}"></script>
  <script src="{% static 'assets/js/modernizr.min.js' %}"></script>
  <script src="{% static 'assets/js/countdown.js' %}"></script>
  <script src="{% static 'assets/js/skill-bar.js' %}"></script>
  <script src="{% static 'assets/js/pricing-switcher.js' %}"></script>
  <script src="{% static 'assets/js/top-to-bottom.js' %}"></script>
  <script src="{% static 'assets/js/gsap.js' %}"></script>
  <script src="{% static 'assets/js/ScrollTrigger.js' %}"></script>
  <script src="{% static 'assets/js/SplitText.js' %}"></script>
  <script src="{% static 'assets/js/gsap-animation.js' %}"></script>


  <!-- <script src="{% static 'assets/js/scrollsmooth.js' %}"></script> -->
  <script src="{% static 'assets/js/accordion.js' %}"></script>
  <script src="https://maps.googleapis.com/maps/api/js?v=3&key=AIzaSyArZVfNvjnLNwJZlLJKuOiWHZ6vtQzzb1Y"></script>

  <script src="{% static 'assets/js/app.js' %}"></script>
"""

header_file = "templates/campaigns/_header.html"
if os.path.exists(header_file):
    with open(header_file, "r") as f:
        header_content = f.read()
    
    match = re.search(r'(<header class="site-header.*?</header>)', header_content, re.DOTALL)
    if match:
        new_header_content = "{% load static %}\n" + match.group(1) + "\n"
        with open(header_file, "w") as f:
            f.write(new_header_content)
        print(f"Fixed {header_file}")
    else:
        print(f"Failed to find header block in {header_file}")

home_dir = "templates/home"
for filename in os.listdir(home_dir):
    if filename.endswith(".html"):
        filepath = os.path.join(home_dir, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        
        if "assets/js/jquery" not in content and "</body>" in content:
            content = content.replace("</body>", footer_scripts + "</body>")
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"Injected scripts to {filename}")
