// @ts-check
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';
import remarkBreaks from 'remark-breaks';

export default defineConfig({
  site: 'https://wiki.fritecraft.fr',
  // Wiki.js transformait chaque retour à la ligne en saut de ligne
  markdown: { remarkPlugins: [remarkBreaks] },
  // Anciennes URLs Wiki.js (avec accents) -> nouvelles
  redirects: {
    '/packs/raretés': '/packs/raretes',
  },
  integrations: [
    starlight({
      title: 'Fritecraft',
      description: 'Le wiki du serveur Minecraft Fritecraft',
      defaultLocale: 'root',
      locales: { root: { label: 'Français', lang: 'fr' } },
      social: [
        { icon: 'github', label: 'GitHub', href: 'https://github.com/fritecraft' },
      ],
      customCss: ['./src/styles/items.css'],
      editLink: { baseUrl: 'https://github.com/fritecraft/wiki/edit/main/' },
      sidebar: [
        { label: 'Fritecraft', autogenerate: { directory: 'fritecraft' } },
        { label: 'Aventures', autogenerate: { directory: 'aventures' } },
        { label: 'Lore', autogenerate: { directory: 'lore' } },
        { label: 'Tutoriels', autogenerate: { directory: 'tutoriels' } },
        { label: 'Packs', autogenerate: { directory: 'packs' } },
        { label: 'Boutiques', autogenerate: { directory: 'boutiques' } },
        { label: 'Objets', autogenerate: { directory: 'objets' } },
        { label: 'Armes', autogenerate: { directory: 'armes' } },
        { label: 'Progrès', autogenerate: { directory: 'progres' } },
      ],
    }),
  ],
});
