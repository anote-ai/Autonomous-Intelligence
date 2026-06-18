import React from "react";
import { Helmet } from "react-helmet-async";
import { Link } from "react-router-dom";
import Navbar from "./Navbar";
import Footer from "./Footer";
import { BLOG_POSTS } from "./landingPageData";

function BlogPage() {
  return (
    <div className="min-h-screen bg-white dark:bg-[#212121] text-gray-900 dark:text-white flex flex-col">
      <Helmet>
        <title>Blog | Panacea by Anote</title>
        <meta
          name="description"
          content="Updates and engineering notes from the team building Panacea, Anote's Autonomous Intelligence platform."
        />
        <link rel="canonical" href="https://anote.ai/blog" />
      </Helmet>

      <Navbar />
      <main className="flex-1 mx-auto max-w-3xl w-full px-6 py-16">
        <h1 className="text-3xl font-semibold">Blog</h1>
        <p className="mt-4 text-gray-600 dark:text-gray-300">
          Updates and engineering notes from the team building Panacea.
        </p>

        <div className="mt-10 space-y-10">
          {BLOG_POSTS.map((post) => (
            <article key={post.slug} id={post.slug} className="border-t border-gray-200 dark:border-gray-700 pt-8">
              <p className="text-xs text-gray-400 dark:text-gray-500">
                {new Date(post.date).toLocaleDateString(undefined, {
                  year: "numeric",
                  month: "long",
                  day: "numeric",
                })}
              </p>
              <h2 className="mt-2 text-xl font-semibold">{post.title}</h2>
              <p className="mt-3 text-gray-600 dark:text-gray-300">{post.excerpt}</p>
              <p className="mt-3 text-gray-600 dark:text-gray-300">{post.body}</p>
            </article>
          ))}
        </div>

        <p className="mt-12 text-sm text-gray-500 dark:text-gray-400">
          Want updates in your inbox?{" "}
          <Link to="/register" className="text-gray-900 dark:text-white font-medium hover:underline">
            Create an account
          </Link>{" "}
          or{" "}
          <Link to="/contact" className="text-gray-900 dark:text-white font-medium hover:underline">
            get in touch
          </Link>
          .
        </p>
      </main>
      <Footer />
    </div>
  );
}

export default BlogPage;
