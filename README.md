<!-- Improved compatibility of back to top link: See: https://github.com/K9Developer/Cubicle/pull/73 -->
<a id="readme-top"></a>
<!--
*** Thanks for checking out the Best-README-Template. If you have a suggestion
*** that would make this better, please fork the repo and create a pull request
*** or simply open an issue with the tag "enhancement".
*** Don't forget to give the project a star!
*** Thanks again! Now go create something AMAZING! :D
-->



<!-- PROJECT SHIELDS -->
<!--
*** I'm using markdown "reference style" links for readability.
*** Reference links are enclosed in brackets [ ] instead of parentheses ( ).
*** See the bottom of this document for the declaration of the reference variables
*** for contributors-url, forks-url, etc. This is an optional, concise syntax you may use.
*** https://www.markdownguide.org/basic-syntax/#reference-style-links
-->
[![Contributors][contributors-shield]][contributors-url]
[![Forks][forks-shield]][forks-url]
[![Stargazers][stars-shield]][stars-url]
[![Issues][issues-shield]][issues-url]
[![Unlicense License][license-shield]][license-url]
[![LinkedIn][linkedin-shield]][linkedin-url]



<!-- PROJECT LOGO -->
<br />
<div align="center">
  <a href="https://github.com/K9Developer/Cubicle">
    <img src="assets/hsec.png" alt="Logo" width="80" height="80">
  </a>

  <h3 align="center">HSEC</h3>

  <p align="center">
    A security system made from scratch.
    <br />
    <br />
    <a href="https://youtu.be/8Xbfi7PUUHs">View Demo</a>
    &middot;
    <a href="https://github.com/K9Developer/Cubicle/issues/new">Report Bug</a>
    &middot;
    <a href="https://github.com/K9Developer/Cubicle/issues/new">Request Feature</a>
  </p>
</div>



<!-- TABLE OF CONTENTS -->
<details>
  <summary>Table of Contents</summary>
  <ol>
    <li>
      <a href="#about-the-project">About The Project</a>
      <ul>
        <li><a href="#built-with">Built With</a></li>
      </ul>
    </li>
    <li>
      <a href="#getting-started">Getting Started</a>
      <ul>
        <li><a href="#prerequisites">Prerequisites</a></li>
        <li><a href="#installation">Installation</a></li>
      </ul>
    </li>
    <li><a href="#usage">Usage</a></li>
    <li><a href="#roadmap">Roadmap</a></li>
    <li><a href="#contributing">Contributing</a></li>
    <li><a href="#license">License</a></li>
    <li><a href="#contact">Contact</a></li>
    <li><a href="#acknowledgments">Acknowledgments</a></li>
  </ol>
</details>



<!-- ABOUT THE PROJECT -->
## About The Project

<img src="https://socialify.git.ci/K9Developer/HSEC/image?name=1&owner=1&stargazers=1&theme=Dark">

This project is a security camera manager. It includes the firmware of the camera written in CPP ([here](https://github.com/K9Developer/HSEC/tree/master/camera_module/camera)), it has the web server for the actual camera viewer and client written in ReactTS ([here](https://github.com/K9Developer/HSEC/tree/master/hsec-client)), it also has the main server that communicates with the users and cameras ([here](https://github.com/K9Developer/HSEC/tree/master/central_server)). It also includes a script to view the camera's logs ([here](https://github.com/K9Developer/HSEC/tree/master/camera_module/camera_interact)).

More information about the custom protocol itself (that is built ontop of TCP) can be found [here](https://github.com/K9Developer/HSEC/blob/master/README.pdf).
<p align="right">(<a href="#readme-top">back to top</a>)</p>



### Built With

##### Web client
[![React][React-ico]][React-url]

##### Main Server
[![Python][Python-ico]][Python-url]

##### Camera
[![CPP][CPP-ico]][CPP-url]
[![PIO][PIO-ico]][PIO-url]



<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- GETTING STARTED -->
## Getting Started

### Prerequisites

First, you'd need to buy the camera or a compatible product. I used [this](https://www.waveshare.com/wiki/ESP32-S3-ETH).

### Installation - Camera

1. Clone the repo
   ```sh
   git clone https://github.com/K9Developer/HSEC.git
   ```
2. Connect the camera to the board
3. Connect the board to the computer
4. Connect an Ethernet cable to the board
5. Install platform IO
6. Compile and upload the code `pio run --target upload`
7. Hold the BOOT button for a few seconds to ensure a full reset

If also want to read the camera's logs you can:
1. run `cd HSEC/camera_module/camera_interact`
2. Install dependecies: `pip install -r requirements.txt`
3. Run using `python camera_interact.py`

### Installation - Webserver

1. Clone the repo
   ```sh
   git clone https://github.com/K9Developer/HSEC.git
   ```
2. Install NodeJS
3. Install yarn
4. Run `cd HSEC/hsec-client && yarn install` to install dependecies
5. Launch the server with `yarn run`

### Installation - Central/Main Server

1. Clone the repo
   ```sh
   git clone https://github.com/K9Developer/HSEC.git
   ```
2. run `cd HSEC/central_server` and `pip install -r requirements.txt`
3. then run `python -m main`

<p align="right">(<a href="#readme-top">back to top</a>)</p>


<!-- ROADMAP -->
## Roadmap

- [x] Add redzones
- [x] Add camera sharing
- [x] Add forgot password
- [ ] Fix a few possible replay vulnerabilties
- [x] Camera sharing
- [x] Camera playback - view history (WIP)


See the [open issues](https://github.com/K9Developer/Cubicle/issues) for a full list of proposed features (and known issues).

<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- CONTRIBUTING -->
## Contributing

Contributions are what make the open source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**.

If you have a suggestion that would make this better, please fork the repo and create a pull request. You can also simply open an issue with the tag "enhancement".
Don't forget to give the project a star! Thanks again!

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

### Top contributors:

<a href="https://github.com/K9Developer/Cubicle/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=K9Developer/Cubicle" alt="contrib.rocks image" />
</a>

<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- LICENSE -->
## License

Distributed under the Unlicense License. See `LICENSE` for more information.

<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- CONTACT -->
## Contact

Ilai - ilai.keinan@gmail.com

<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- MARKDOWN LINKS & IMAGES -->
<!-- https://www.markdownguide.org/basic-syntax/#reference-style-links -->
[contributors-shield]: https://img.shields.io/github/contributors/K9Developer/Cubicle.svg?style=for-the-badge
[contributors-url]: https://github.com/K9Developer/Cubicle/graphs/contributors
[forks-shield]: https://img.shields.io/github/forks/K9Developer/Cubicle.svg?style=for-the-badge
[forks-url]: https://github.com/K9Developer/Cubicle/network/members
[stars-shield]: https://img.shields.io/github/stars/K9Developer/Cubicle.svg?style=for-the-badge
[stars-url]: https://github.com/K9Developer/Cubicle/stargazers
[issues-shield]: https://img.shields.io/github/issues/K9Developer/Cubicle.svg?style=for-the-badge
[issues-url]: https://github.com/K9Developer/Cubicle/issues
[license-shield]: https://img.shields.io/github/license/K9Developer/Cubicle.svg?style=for-the-badge
[license-url]: https://github.com/K9Developer/Cubicle/blob/master/LICENSE.txt
[linkedin-shield]: https://img.shields.io/badge/-LinkedIn-black.svg?style=for-the-badge&logo=linkedin&colorB=555
[linkedin-url]: https://linkedin.com/in/othneildrew
[product-screenshot]: images/screenshot.png


[React-url]: https://reactjs.org/
[Python-url]: https://www.python.org/
[PIO-url]: https://platformio.org/
[CPP-url]: https://cplusplus.com/


[React-ico]: https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB
[Python-ico]: https://img.shields.io/badge/Python-20232A?style=for-the-badge&logo=python&logoColor=61DAFB
[PIO-ico]: https://img.shields.io/badge/Platformio-20232A?style=for-the-badge&logo=platformio&logoColor=61DAFB
[CPP-ico]: https://img.shields.io/badge/C++-20232A?style=for-the-badge&logo=cplusplus&logoColor=61DAFB

