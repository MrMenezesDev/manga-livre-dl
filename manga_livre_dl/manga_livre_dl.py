from requests import Session
from pathlib import Path
import tqdm
from PIL import Image
import shutil


class MangaLivreDl:
    def __init__(self, final_path, no_pdf):
        self.final_path = Path(final_path)
        self.no_pdf = no_pdf
        self.session = Session()
        self.session.headers.update({
            'authority': 'mangalivre.net',
            'accept': 'application/json, text/javascript, */*; q=0.01',
            'accept-language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7,zh-CN;q=0.6,zh;q=0.5,ru;q=0.4,es;q=0.3,ja;q=0.2',
            'sec-ch-ua': '"Not?A_Brand";v="8", "Chromium";v="108", "Google Chrome";v="108"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36',
            'x-requested-with': 'XMLHttpRequest'
        })
    

    def get_manga_chapters(self, url, chapter_selection):
        manga_id = url.split('/')[-1]
        manga_chapters = []
        offset = 0
        while True:
            response = self.session.get(f'https://mangalivre.net/series/chapters_list.json?page={offset}&id_serie={manga_id}').json()['chapters']
            if not response:
                break
            manga_chapters.extend(response)
            offset += 1
            if chapter_selection[0] == 'all':
                continue
            if chapter_selection[0] == 'last':
                break
        manga_chapters.reverse()
        for i, cha1 in enumerate(manga_chapters):
            count = 1
            for cha2 in manga_chapters[i + 1:]:
                if cha1['number'] == cha2['number']:
                    cha2['number'] = f'{cha2["number"]}_{count}'
                    count += 1
        if chapter_selection[0] == 'last':
            manga_chapters = [manga_chapters[-1]]
        elif chapter_selection[0] != 'all':
            manga_chapters = [manga_chapter for manga_chapter in manga_chapters if manga_chapter['number'] in chapter_selection]
        if not manga_chapters:
            raise Exception('No chapters found.')
        return manga_chapters

    
    def get_sanizated_string(self, dirty_string, is_folder):
        for character in ['\\', '/', ':', '*', '?', '"', '<', '>', '|']:
            dirty_string = dirty_string.replace(character, '_')
        if dirty_string[-1:] == '.' and is_folder:
            dirty_string = dirty_string[:-1] + '_'
        return dirty_string.strip()


    def get_final_location(self, chapter):
        return self.final_path / self.get_sanizated_string(chapter["name"], True) / f'Chapter {self.get_sanizated_string(chapter["number"], True)}'
    

    def check_exists(self, final_location):
        if final_location.exists() or (final_location.parent / (final_location.name + '.pdf')).exists():
            return True

    
    def download_manga_chapter(self, chapter, final_location):
        manga_chapter_images_url = [i['legacy'] for i in self.session.get(f'https://mangalivre.net/leitor/pages/{chapter["releases"][list(chapter["releases"].keys())[0]]["id_release"]}.json').json()['images']]
        manga_chapter_images_session = [self.session.get(i, stream = True) for i in manga_chapter_images_url]
        total_size_in_bytes = sum(int(i.headers.get('content-length', 0)) for i in manga_chapter_images_session)
        progress_bar = tqdm.tqdm(total = total_size_in_bytes, unit = 'iB', unit_scale = True, leave = False)
        final_location.mkdir(parents = True, exist_ok = True)
        for i, response in enumerate(manga_chapter_images_session):
            if 'image' in response.headers['content-type']:
                with open(final_location / f'{i:02d}.{response.url.split(".")[-1]}', 'wb') as file:
                    for data in response.iter_content(1024):
                        progress_bar.update(len(data))
                        file.write(data)
        progress_bar.close()
    

    def make_pdf(self, final_location):
        if not self.no_pdf:
            images = [Image.open(i) for i in final_location.glob('*')]
            images[0].save(
                final_location.parent / (final_location.name + '.pdf'),
                save_all = True,
                append_images = images[1:],
                quality = 80
            )
            shutil.rmtree(final_location)
